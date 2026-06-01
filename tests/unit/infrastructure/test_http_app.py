"""Tests for the FastAPI HTTP application."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.infrastructure.http.app import create_app


class _StubNotifier(MatchNotifier):
    """In-memory notifier for testing."""

    def __init__(self):
        self.closed = []

    async def on_match_closed(self, meetup):
        self.closed.append(meetup)

    async def on_meetup_updated(self, meetup):
        pass


def _make_app(finish_side_effect=None, finish_return=None):
    container = MagicMock()
    notifier = _StubNotifier()
    if finish_side_effect:
        container.finish_match.return_value.execute.side_effect = finish_side_effect
    elif finish_return is not None:
        container.finish_match.return_value.execute.return_value = finish_return
    return create_app(container, notifier), notifier


_VALID_BODY = {
    "meetup_date": "2026-04-30",
    "events": [],
    "finalScore": {"A": 2, "B": 1},
}


@pytest.mark.asyncio
async def test_finish_match_success_calls_notifier():
    meetup = MagicMock()
    meetup.result.score_a = 2
    meetup.result.score_b = 1
    app, notifier = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 200
    assert len(notifier.closed) == 1
    assert notifier.closed[0] is meetup


@pytest.mark.asyncio
async def test_finish_match_success_returns_score():
    meetup = MagicMock()
    meetup.result.score_a = 2
    meetup.result.score_b = 1
    app, _ = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.json() == {
        "meetup_date": "2026-04-30",
        "score_a": 2,
        "score_b": 1,
    }


@pytest.mark.asyncio
async def test_finish_match_404_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=MeetupNotFoundError("2026-04-30"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 404
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_finish_match_409_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=MeetupAlreadyClosedError("closed"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 409
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_finish_match_422_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=ValueError("bad date"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 422
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_auth_enforced_when_tokens_configured():
    """create_app registers auth middleware when tokens are provided."""
    container = MagicMock()
    notifier = _StubNotifier()
    auth_app = create_app(container, notifier, match_token="match-tok", manage_token="manage-tok")
    async with AsyncClient(
        transport=ASGITransport(app=auth_app), base_url="http://test"
    ) as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)
    assert response.status_code == 401


class TestActiveMatch:
    """Tests for GET /api/match/active."""

    @pytest.mark.asyncio
    async def test_returns_200_with_team_data(self):
        """Returns team data for the most recent unfinished meetup with teams."""
        meetup = MagicMock()
        meetup.result = None
        meetup.date = datetime(2026, 5, 26, 20, 0)

        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_b = MagicMock()
        pid_b.value = "p2"
        meetup.teams = [MagicMock(players=[pid_a]), MagicMock(players=[pid_b])]

        player_a = MagicMock()
        player_a.id.value = "p1"
        player_a.name = "Juande"
        player_b = MagicMock()
        player_b.id.value = "p2"
        player_b.name = "David"

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [meetup]
        container.player_repository.find_all.return_value = [player_a, player_b]
        container.team_colors = ("blanco", "negro")
        container.team_hex_bg = ("#e4e4e7", "#27272a")
        container.team_hex_text = ("#27272a", "#e4e4e7")

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-05-26T20:00"
        assert data["teamA"] == ["Juande"]
        assert data["teamB"] == ["David"]
        assert data["nameA"] == "Blanco"
        assert data["nameB"] == "Negro"
        assert data["colorA"] == "#e4e4e7"
        assert data["colorTextA"] == "#27272a"
        assert data["colorB"] == "#27272a"
        assert data["colorTextB"] == "#e4e4e7"

    @pytest.mark.asyncio
    async def test_returns_404_when_no_active_meetup(self):
        """404 when there are no meetups with teams that are unfinished."""
        container = MagicMock()
        container.meetup_repository.find_all.return_value = []
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ignores_finished_meetups(self):
        """A meetup with result set is not considered active."""
        finished = MagicMock()
        finished.teams = [MagicMock(), MagicMock()]
        finished.result = MagicMock()  # not None → finished

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [finished]
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ignores_meetups_without_teams(self):
        """A meetup with teams=None is not considered active."""
        no_teams = MagicMock()
        no_teams.teams = None
        no_teams.result = None

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [no_teams]
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")
        assert response.status_code == 404


class TestMeetupActive:
    """Tests for GET /api/meetup/active."""

    @pytest.mark.asyncio
    async def test_returns_404_when_no_meetups(self):
        """404 when the repository is empty."""
        container = MagicMock()
        container.meetup_repository.find_all.return_value = []
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/meetup/active")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_when_all_meetups_finished(self):
        """404 when every meetup has a result set."""
        finished = MagicMock()
        finished.result = MagicMock()  # not None → finished
        container = MagicMock()
        container.meetup_repository.find_all.return_value = [finished]
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/meetup/active")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_players_and_null_teams_when_no_teams(self):
        """200 with sorted players list and teams=null for a meetup without teams."""
        meetup = MagicMock()
        meetup.result = None
        meetup.teams = None
        meetup.date = datetime(2026, 5, 28, 20, 0)
        pid = MagicMock()
        pid.value = "p1"
        meetup.players = [pid]

        player = MagicMock()
        player.id.value = "p1"
        player.name = "Juande"

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [meetup]
        container.player_repository.find_all.return_value = [player]

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/meetup/active")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-05-28T20:00"
        assert data["players"] == [{"id": "p1", "name": "Juande"}]
        assert data["teams"] is None

    @pytest.mark.asyncio
    async def test_returns_full_payload_when_teams_exist(self):
        """200 with players list and populated teams object when meetup has teams."""
        meetup = MagicMock()
        meetup.result = None
        meetup.date = datetime(2026, 5, 28, 20, 0)
        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_b = MagicMock()
        pid_b.value = "p2"
        meetup.players = [pid_a, pid_b]
        meetup.teams = [MagicMock(players=[pid_a]), MagicMock(players=[pid_b])]

        player_a = MagicMock()
        player_a.id.value = "p1"
        player_a.name = "Juande"
        player_b = MagicMock()
        player_b.id.value = "p2"
        player_b.name = "David"

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [meetup]
        container.player_repository.find_all.return_value = [player_a, player_b]
        container.team_colors = ("blanco", "negro")
        container.team_hex_bg = ("#e4e4e7", "#27272a")
        container.team_hex_text = ("#27272a", "#e4e4e7")
        container.team_emojis = ("⚪", "⚫")
        container.start_match.return_value.execute.return_value = "http://test/match"

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/meetup/active")

        assert response.status_code == 200
        data = response.json()
        assert data["players"] == [
            {"id": "p2", "name": "David"},
            {"id": "p1", "name": "Juande"},
        ]
        teams = data["teams"]
        assert teams["teamA"] == ["Juande"]
        assert teams["teamB"] == ["David"]
        assert teams["nameA"] == "Blanco"
        assert teams["nameB"] == "Negro"
        assert teams["emojiA"] == "⚪"
        assert teams["emojiB"] == "⚫"
        assert teams["colorA"] == "#e4e4e7"
        assert teams["colorTextA"] == "#27272a"
        assert teams["colorB"] == "#27272a"
        assert teams["colorTextB"] == "#e4e4e7"
        assert teams["emojiB"] == "⚫"
        assert teams["matchUrl"] == "http://test/match"

    @pytest.mark.asyncio
    async def test_uses_match_token_url_when_configured(self):
        """matchUrl uses base_url + token path when match_token is set."""
        meetup = MagicMock()
        meetup.result = None
        meetup.date = datetime(2026, 5, 28, 20, 0)
        pid = MagicMock()
        pid.value = "p1"
        meetup.players = [pid]
        meetup.teams = [MagicMock(players=[pid]), MagicMock(players=[])]

        player = MagicMock()
        player.id.value = "p1"
        player.name = "Juande"

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [meetup]
        container.player_repository.find_all.return_value = [player]
        container.team_colors = ("blanco", "negro")
        container.team_hex_bg = ("#e4e4e7", "#27272a")
        container.team_hex_text = ("#27272a", "#e4e4e7")
        container.team_emojis = ("⚪", "⚫")
        container.base_url = "https://pyball.example.com"

        app = create_app(
            container,
            _StubNotifier(),
            match_token="my-match-tok",
            manage_token="my-manage-tok",
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"pyball_manage_token": "my-manage-tok"},
        ) as c:
            response = await c.get("/api/meetup/active")

        assert response.status_code == 200
        assert response.json()["teams"]["matchUrl"] == (
            "https://pyball.example.com/match?token=my-match-tok"
        )


class TestMatchEvents:
    """Tests for GET /api/match/{date}/events."""

    def _make_closed_meetup(self):
        """Return a mock closed meetup with one goal event."""
        ev = MagicMock()
        ev.scorer_id.value = "p1"
        ev.assistant_id = None
        ev.team = "A"
        ev.timestamp.strftime.return_value = "20:15"

        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_b = MagicMock()
        pid_b.value = "p2"

        meetup = MagicMock()
        meetup.is_closed.return_value = True
        meetup.date = datetime(2026, 5, 28, 20, 0)
        meetup.result.events = (ev,)
        meetup.teams = [MagicMock(players=[pid_a]), MagicMock(players=[pid_b])]
        return meetup

    def _make_players(self):
        """Return two mock player objects."""
        player_a = MagicMock()
        player_a.id.value = "p1"
        player_a.name = "Dani"
        player_b = MagicMock()
        player_b.id.value = "p2"
        player_b.name = "Rafa"
        return [player_a, player_b]

    @pytest.mark.asyncio
    async def test_returns_200_with_event_data(self):
        """Returns team names, colours, and events (newest-first) for a closed meetup."""
        meetup = self._make_closed_meetup()
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.player_repository.find_all.return_value = self._make_players()
        container.team_colors = ("blanco", "negro")
        container.team_hex_bg = ("#ffffff", "#27272a")
        container.team_hex_text = ("#27272a", "#e4e4e7")

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/2026-05-28T20:00/events")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-05-28T20:00"
        assert data["nameA"] == "Blanco"
        assert data["nameB"] == "Negro"
        assert data["teamA"] == ["Dani"]
        assert data["teamB"] == ["Rafa"]
        assert data["colorA"] == "#ffffff"
        assert data["colorB"] == "#27272a"
        assert data["colorTextA"] == "#27272a"
        assert data["colorTextB"] == "#e4e4e7"
        assert len(data["events"]) == 1
        assert data["events"][0]["scorer"] == "Dani"
        assert data["events"][0]["assistant"] is None
        assert data["events"][0]["team"] == "A"
        assert data["events"][0]["timestamp"] == "20:15"

    @pytest.mark.asyncio
    async def test_returns_404_when_meetup_not_found(self):
        """Returns 404 when no meetup exists on that date."""
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = None

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/2026-05-28T20:00/events")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_409_when_meetup_not_closed(self):
        """Returns 409 when the meetup exists but has no result yet."""
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/2026-05-28T20:00/events")

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_returns_422_on_invalid_date(self):
        """Returns 422 when the date path parameter is not a valid ISO datetime."""
        container = MagicMock()
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/not-a-date/events")

        assert response.status_code == 422
