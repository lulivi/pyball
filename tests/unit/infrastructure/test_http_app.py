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


def _make_app(container=None, finish_side_effect=None, finish_return=None):
    if container is None:
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
        container.get_active_meetup.return_value.execute.return_value = meetup
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
        """404 when GetActiveMeetup raises MeetupNotFoundError."""
        container = MagicMock()
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError(
            "active"
        )
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")
        assert response.status_code == 404


class TestMeetupActive:
    """Tests for GET /api/meetup/active."""

    @pytest.mark.asyncio
    async def test_returns_404_when_active_meetup_service_raises(self):
        """404 when GetActiveMeetup raises MeetupNotFoundError."""
        container = MagicMock()
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError(
            "active"
        )
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
        container.get_active_meetup.return_value.execute.return_value = meetup
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
        container.get_active_meetup.return_value.execute.return_value = meetup
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
        """matchUrl is built by StartMatch.execute(), which now returns the token URL."""
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
        container.get_active_meetup.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = [player]
        container.team_colors = ("blanco", "negro")
        container.team_hex_bg = ("#e4e4e7", "#27272a")
        container.team_hex_text = ("#27272a", "#e4e4e7")
        container.team_emojis = ("⚪", "⚫")
        container.start_match.return_value.execute.return_value = (
            "https://pyball.example.com/match?token=my-match-tok"
        )

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


class TestEditMatchResult:
    """Tests for POST /api/match/{date}/edit."""

    _EDIT_BODY = {
        "meetup_date": "2026-05-28T20:00",
        "events": [],
        "finalScore": {"A": 0, "B": 0},
    }

    @pytest.mark.asyncio
    async def test_returns_200_and_calls_notifier(self):
        """Returns score and fires notifier for a closed meetup."""
        meetup = MagicMock()
        meetup.is_closed.return_value = True
        meetup.result.score_a = 0
        meetup.result.score_b = 0

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.edit_match_result.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/api/match/2026-05-28T20:00/edit", json=self._EDIT_BODY)

        assert response.status_code == 200
        data = response.json()
        assert data["score_a"] == 0
        assert data["score_b"] == 0
        assert len(notifier.closed) == 1

    @pytest.mark.asyncio
    async def test_returns_404_when_meetup_not_found(self):
        """Returns 404 when no meetup exists on that date."""
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = None

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/api/match/2026-05-28T20:00/edit", json=self._EDIT_BODY)

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
            response = await c.post("/api/match/2026-05-28T20:00/edit", json=self._EDIT_BODY)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_returns_422_on_use_case_value_error(self):
        """Returns 422 when the use case raises ValueError (e.g. player not found)."""
        meetup = MagicMock()
        meetup.is_closed.return_value = True

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.edit_match_result.return_value.execute.side_effect = ValueError("bad player")

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/api/match/2026-05-28T20:00/edit", json=self._EDIT_BODY)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_does_not_call_notifier_on_error(self):
        """Notifier is not called when the use case raises an error."""
        meetup = MagicMock()
        meetup.is_closed.return_value = True

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.edit_match_result.return_value.execute.side_effect = ValueError("bad player")

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/api/match/2026-05-28T20:00/edit", json=self._EDIT_BODY)

        assert len(notifier.closed) == 0

    @pytest.mark.asyncio
    async def test_returns_422_on_invalid_date(self):
        """Returns 422 when the date path parameter is not a valid ISO datetime."""
        container = MagicMock()
        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post(
                "/api/match/not-a-date/edit",
                json={"meetup_date": "", "events": [], "finalScore": {"A": 0, "B": 0}},
            )

        assert response.status_code == 422


class TestManifests:
    """Tests for GET /manifest-match.json and GET /manifest-manage.json."""

    def _make_named_app(self, name: str = "Tensores"):
        container = MagicMock()
        container.name = name
        return create_app(container, _StubNotifier())

    @pytest.mark.asyncio
    async def test_match_manifest_name(self):
        """Match manifest name includes 'Partido' and the instance name."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-match.json")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PyBall – Partido Tensores"
        assert data["short_name"] == "Partido Tensores"

    @pytest.mark.asyncio
    async def test_manage_manifest_name(self):
        """Manage manifest name includes 'Gestión' and the instance name."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-manage.json")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PyBall – Gestión Tensores"
        assert data["short_name"] == "Gestión Tensores"

    @pytest.mark.asyncio
    async def test_match_manifest_scope(self):
        """Match manifest has scope /match and id /match."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-match.json")
        data = response.json()
        assert data["scope"] == "/match"
        assert data["id"] == "/match"

    @pytest.mark.asyncio
    async def test_manage_manifest_scope(self):
        """Manage manifest has scope /manage and id /manage."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-manage.json")
        data = response.json()
        assert data["scope"] == "/manage"
        assert data["id"] == "/manage"

    @pytest.mark.asyncio
    async def test_match_manifest_static_fields(self):
        """Match manifest contains the expected static fields."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-match.json")
        data = response.json()
        assert data["start_url"] == "/match"
        assert data["display"] == "standalone"
        assert data["background_color"] == "#0f172a"
        assert data["theme_color"] == "#0f172a"
        assert len(data["icons"]) == 2
        assert data["scope"] == "/match"

    @pytest.mark.asyncio
    async def test_manage_manifest_static_fields(self):
        """Manage manifest contains the expected static fields."""
        app = self._make_named_app("Tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-manage.json")
        data = response.json()
        assert data["start_url"] == "/manage"
        assert data["display"] == "standalone"
        assert data["background_color"] == "#0f172a"
        assert data["theme_color"] == "#0f172a"
        assert len(data["icons"]) == 2
        assert data["scope"] == "/manage"


class TestPathPrefix:
    """Tests for create_app with a non-empty path_prefix."""

    def _make_prefixed_app(self, prefix: str = "tensores", tmp_path=None):
        container = MagicMock()
        container.name = "Tensores"
        kwargs: dict = {"path_prefix": prefix}
        if tmp_path is not None:
            kwargs["static_dir"] = tmp_path
        return create_app(container, _StubNotifier(), **kwargs)

    @pytest.mark.asyncio
    async def test_manifest_match_served_at_prefixed_path(self):
        """GET /{prefix}/manifest-match.json returns 200."""
        app = self._make_prefixed_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/manifest-match.json")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_manifest_match_has_prefixed_scope_id_start_url_icons(self):
        """Match manifest fields all carry the path prefix."""
        app = self._make_prefixed_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/manifest-match.json")
        data = response.json()
        assert data["scope"] == "/tensores/match"
        assert data["id"] == "/tensores/match"
        assert data["start_url"] == "/tensores/match"
        assert data["icons"][0]["src"] == "/tensores/icons/icon-192.png"
        assert data["icons"][1]["src"] == "/tensores/icons/icon-512.png"

    @pytest.mark.asyncio
    async def test_manifest_manage_has_prefixed_scope_id_start_url_icons(self):
        """Manage manifest fields all carry the path prefix."""
        app = self._make_prefixed_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/manifest-manage.json")
        data = response.json()
        assert data["scope"] == "/tensores/manage"
        assert data["id"] == "/tensores/manage"
        assert data["start_url"] == "/tensores/manage"
        assert data["icons"][0]["src"] == "/tensores/icons/icon-192.png"

    @pytest.mark.asyncio
    async def test_api_route_served_at_prefixed_path(self):
        """GET /{prefix}/api/match/active is handled (not 404)."""
        container = MagicMock()
        container.name = "T"
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("x")
        app = create_app(container, _StubNotifier(), path_prefix="tensores")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/api/match/active")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_root_path_returns_404_when_prefix_set(self):
        """GET /match returns 404 when routes are mounted under a prefix."""
        app = self._make_prefixed_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/match")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_sw_js_served_at_prefixed_path_with_substitution(self, tmp_path):
        """GET /{prefix}/sw.js returns the SW with placeholders substituted."""
        (tmp_path / "sw.js").write_text("BASE=__PYBALL_BASE__ SLUG=__PYBALL_SLUG__")
        app = self._make_prefixed_app(tmp_path=tmp_path)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/sw.js")
        assert response.status_code == 200
        assert "BASE=/tensores" in response.text
        assert "SLUG=tensores" in response.text
        assert "__PYBALL_BASE__" not in response.text

    @pytest.mark.asyncio
    async def test_match_html_served_with_prefix_injected(self, tmp_path):
        """GET /{prefix}/match returns HTML with __PYBALL_BASE__ substituted."""
        (tmp_path / "match.html").write_text("<html>__PYBALL_BASE__/api/match</html>")
        app = self._make_prefixed_app(tmp_path=tmp_path)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/tensores/match")
        assert response.status_code == 200
        assert "/tensores/api/match" in response.text
        assert "__PYBALL_BASE__" not in response.text

    @pytest.mark.asyncio
    async def test_no_prefix_routes_remain_at_root(self):
        """With path_prefix='', manifest routes stay at /manifest-match.json."""
        container = MagicMock()
        container.name = "T"
        app = create_app(container, _StubNotifier(), path_prefix="")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manifest-match.json")
        data = response.json()
        assert data["scope"] == "/match"
        assert data["id"] == "/match"

    @pytest.mark.asyncio
    async def test_no_prefix_sw_js_slug_is_default(self, tmp_path):
        """With path_prefix='', __PYBALL_SLUG__ is replaced with 'default'."""
        (tmp_path / "sw.js").write_text("SLUG=__PYBALL_SLUG__")
        container = MagicMock()
        container.name = "T"
        app = create_app(container, _StubNotifier(), static_dir=tmp_path, path_prefix="")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/sw.js")
        assert "SLUG=default" in response.text


class TestCreateMeetup:
    """Tests for POST /api/meetup/create."""

    @pytest.mark.asyncio
    async def test_create_meetup_returns_players_and_no_teams(self):
        """POST /api/meetup/create creates meetup, returns players list with teams=null."""
        from pyball.domain.meetup.models import Meetup, PlayerId

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        p_id = PlayerId.generate()
        meetup.add_player(p_id)

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = None
        container.create_meetup.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = []

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": [str(p_id.value)]},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["date"] == "2026-06-08T20:00"
        assert body["teams"] is None
        assert isinstance(body["players"], list)

    @pytest.mark.asyncio
    async def test_create_meetup_resets_existing_meetup(self):
        """POST /api/meetup/create clears players/teams on an existing open meetup."""
        from pyball.domain.meetup.models import Meetup, PlayerId, Team

        date = datetime(2026, 6, 8, 20, 0)
        existing = Meetup.create(date=date, location="Parque Central")
        old_player = PlayerId.generate()
        existing.add_player(old_player)
        existing.set_teams([Team.create("A", [old_player]), Team.create("B", [])])

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.player_repository.find_all.return_value = []

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 200
        assert resp.json()["teams"] is None
        assert existing.teams is None
        assert existing.players == []

    @pytest.mark.asyncio
    async def test_create_meetup_409_when_match_already_finished(self):
        """POST /api/meetup/create returns 409 if the existing meetup is closed."""
        meetup = MagicMock()
        meetup.is_closed.return_value = True

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_meetup_422_on_bad_date(self):
        """POST /api/meetup/create returns 422 for unparseable date strings."""
        app, _ = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "not-a-date", "player_ids": []},
            )

        assert resp.status_code == 422


class TestGenerateTeams:
    """Tests for POST /api/meetup/generate-teams."""

    @pytest.mark.asyncio
    async def test_generate_teams_404_when_no_meetup(self):
        """POST /api/meetup/generate-teams returns 404 when no meetup exists at the given date."""
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = None

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_teams_409_when_match_finished(self):
        """POST /api/meetup/generate-teams returns 409 when the meetup is already closed."""
        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = True
        container.meetup_repository.find_by_datetime.return_value = meetup

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_generate_teams_422_on_bad_date(self):
        """POST /api/meetup/generate-teams returns 422 for unparseable date strings."""
        app, _ = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "not-a-date", "algorithm": "balanceado"},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_teams_422_when_create_teams_raises(self):
        """POST /api/meetup/generate-teams returns 422 when create_teams raises ValueError."""
        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.create_teams.return_value.execute.side_effect = ValueError(
            "Need at least 2 players"
        )

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_teams_calls_create_teams_and_returns_200(self):
        """POST /api/meetup/generate-teams calls create_teams and returns the active meetup."""
        from unittest.mock import patch

        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = meetup

        expected = {"date": "2026-06-08T20:00", "players": [], "teams": {"teamA": [], "teamB": []}}

        app, _ = _make_app(container=container)
        with patch("pyball.infrastructure.http.app._build_meetup_active_response") as mock_build:
            mock_build.return_value = expected
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/generate-teams",
                    json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
                )

        assert resp.status_code == 200
        container.create_teams.assert_called_once_with("balanceado")
        mock_build.assert_called_once_with(container)
