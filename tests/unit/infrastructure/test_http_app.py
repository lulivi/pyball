"""Tests for the FastAPI HTTP application."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.errors import (
    MeetupAlreadyClosedError,
    MeetupHasNoTeamsError,
    MeetupNotFoundError,
)
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from pyball.domain.player.models import Player
from pyball.infrastructure.http.app import create_app


class TestGetNextDefaultDate:
    """Tests for the _get_next_default_date helper."""

    def test_rolls_forward_to_target_weekday(self):
        """From a Monday, targeting Wednesday rolls forward 2 days."""
        from pyball.infrastructure.http.routes.meetup import _get_next_default_date

        monday = datetime(2026, 6, 8, 10, 0)  # a Monday
        result = _get_next_default_date("wednesday", "20:00", now=monday)

        assert result == datetime(2026, 6, 10, 20, 0)

    def test_rolls_to_next_week_when_today_is_the_target_weekday(self):
        """If today IS the target weekday, rolls forward a full week, not 0 days."""
        from pyball.infrastructure.http.routes.meetup import _get_next_default_date

        wednesday = datetime(2026, 6, 10, 10, 0)  # a Wednesday
        result = _get_next_default_date("wednesday", "20:00", now=wednesday)

        assert result == datetime(2026, 6, 17, 20, 0)

    def test_defaults_to_wednesday_for_unknown_weekday_name(self):
        """An unrecognised weekday name falls back to Wednesday (index 2)."""
        from pyball.infrastructure.http.routes.meetup import _get_next_default_date

        monday = datetime(2026, 6, 8, 10, 0)
        result = _get_next_default_date("not-a-real-day", "20:00", now=monday)

        assert result == datetime(2026, 6, 10, 20, 0)


class _StubNotifier(MatchNotifier):
    """In-memory notifier for testing."""

    def __init__(self):
        self.created = []
        self.closed = []
        self.edited = []
        self.updated = []
        self.cancelled = []
        self.date_changed = []

    async def on_meetup_created(self, meetup):
        """Record the created meetup."""
        self.created.append(meetup)

    async def on_match_closed(self, meetup):
        """Record the closed meetup."""
        self.closed.append(meetup)

    async def on_meetup_updated(self, meetup):
        """Record the updated meetup."""
        self.updated.append(meetup)

    async def on_match_edited(self, meetup):
        """Record the edited meetup."""
        self.edited.append(meetup)

    async def on_meetup_cancelled(self, meetup):
        """Record the cancelled meetup."""
        self.cancelled.append(meetup)

    async def on_meetup_date_changed(self, old_date, meetup):
        """Record the old date and the updated meetup."""
        self.date_changed.append((old_date, meetup))


def _make_app(container=None, finish_side_effect=None, finish_return=None):
    if container is None:
        container = MagicMock()
        container.theme_color = "#0f172a"
        container.icons_dir = ""
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
    meetup.is_closed.return_value = True
    meetup.matches = [MagicMock(result=MagicMock(score_a=2, score_b=1))]
    app, notifier = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 200
    assert len(notifier.closed) == 1
    assert notifier.closed[0] is meetup


@pytest.mark.asyncio
async def test_finish_match_success_returns_score():
    meetup = MagicMock()
    meetup.is_closed.return_value = True
    meetup.matches = [MagicMock(result=MagicMock(score_a=2, score_b=1))]
    app, _ = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.json() == {
        "meetup_date": "2026-04-30",
        "score_a": 2,
        "score_b": 1,
    }


@pytest.mark.asyncio
async def test_finish_match_returns_next_round_with_colors_when_round_advances():
    """next_round carries colorA/colorB/colorTextA/colorTextB for the new pairing."""
    pid_a = MagicMock()
    pid_a.value = "p1"
    pid_b = MagicMock()
    pid_b.value = "p2"

    player_a = MagicMock()
    player_a.id.value = "p1"
    player_a.name = "Dani"
    player_b = MagicMock()
    player_b.id.value = "p2"
    player_b.name = "Rafa"

    team_a_mock = MagicMock(players=[pid_a])
    team_b_mock = MagicMock(players=[pid_b])
    meetup = MagicMock()
    meetup.is_closed.return_value = False
    meetup.teams = [team_a_mock, team_b_mock]
    meetup.matches = [
        MagicMock(result=MagicMock(score_a=2, score_b=1)),
        MagicMock(result=MagicMock(score_a=2, score_b=1)),
    ]
    meetup.current_match.return_value = MagicMock(teams_playing=(team_a_mock, team_b_mock))

    container = MagicMock()
    container.finish_match.return_value.execute.return_value = meetup
    container.player_repository.find_all.return_value = [player_a, player_b]
    container.team_colors = ("blanco", "negro")
    container.team_hex_bg = ("#e4e4e7", "#27272a")
    container.team_hex_text = ("#27272a", "#e4e4e7")
    notifier = _StubNotifier()
    app = create_app(container, notifier)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 200
    next_round = response.json()["next_round"]
    assert next_round["teamA"] == ["Dani"]
    assert next_round["teamB"] == ["Rafa"]
    assert next_round["nameA"] == "Blanco"
    assert next_round["nameB"] == "Negro"
    assert next_round["colorA"] == "#e4e4e7"
    assert next_round["colorB"] == "#27272a"
    assert next_round["colorTextA"] == "#27272a"
    assert next_round["colorTextB"] == "#e4e4e7"
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_finish_match_next_round_colors_follow_each_teams_own_position():
    """Regression test: next_round after a triangular round not involving the

    meetup's first team must not be mislabeled "Blanco"/"Negro" -- each team
    keeps its own configured color regardless of which 2 of the 3 are playing.
    """
    pid_b = MagicMock()
    pid_b.value = "p2"
    pid_c = MagicMock()
    pid_c.value = "p3"

    player_b = MagicMock()
    player_b.id.value = "p2"
    player_b.name = "Rafa"
    player_c = MagicMock()
    player_c.id.value = "p3"
    player_c.name = "Nico"

    team_a_mock = MagicMock(players=[MagicMock(value="p1")])
    team_b_mock = MagicMock(players=[pid_b])
    team_c_mock = MagicMock(players=[pid_c])

    meetup = MagicMock()
    meetup.is_closed.return_value = False
    meetup.teams = [team_a_mock, team_b_mock, team_c_mock]
    meetup.matches = [
        MagicMock(result=MagicMock(score_a=2, score_b=1)),
        MagicMock(result=MagicMock(score_a=2, score_b=1)),
    ]
    # Next round: team C (Rojo) plays team B (Negro) -- C is "A" in this match.
    meetup.current_match.return_value = MagicMock(teams_playing=(team_c_mock, team_b_mock))

    container = MagicMock()
    container.finish_match.return_value.execute.return_value = meetup
    container.player_repository.find_all.return_value = [player_b, player_c]
    container.team_colors = ("blanco", "negro", "rojo")
    container.team_hex_bg = ("#e4e4e7", "#27272a", "#b91c1c")
    container.team_hex_text = ("#27272a", "#e4e4e7", "#fff1f2")
    notifier = _StubNotifier()
    app = create_app(container, notifier)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    next_round = response.json()["next_round"]
    assert next_round["teamA"] == ["Nico"]
    assert next_round["teamB"] == ["Rafa"]
    assert next_round["nameA"] == "Rojo"
    assert next_round["nameB"] == "Negro"
    assert next_round["colorA"] == "#b91c1c"
    assert next_round["colorB"] == "#27272a"


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
        meetup.date = datetime(2026, 5, 26, 20, 0)

        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_b = MagicMock()
        pid_b.value = "p2"
        team_a_mock = MagicMock(players=[pid_a])
        team_b_mock = MagicMock(players=[pid_b])
        meetup.teams = [team_a_mock, team_b_mock]
        meetup.current_match.return_value = MagicMock(teams_playing=(team_a_mock, team_b_mock))

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
    async def test_colors_follow_each_teams_own_position_not_match_order(self):
        """Regression test: a triangular round not involving team A/B must not be

        mislabeled "Blanco"/"Negro" — each team keeps its own configured color
        regardless of which 2 of the 3 teams are currently playing.
        """
        meetup = MagicMock()
        meetup.date = datetime(2026, 5, 26, 20, 0)

        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_c = MagicMock()
        pid_c.value = "p3"
        team_a_mock = MagicMock(players=[pid_a])
        team_b_mock = MagicMock(players=[MagicMock(value="p2")])
        team_c_mock = MagicMock(players=[pid_c])
        meetup.teams = [team_a_mock, team_b_mock, team_c_mock]
        # Current round: team C (Rojo) plays team A (Blanco) -- C is "A" in this match.
        meetup.current_match.return_value = MagicMock(teams_playing=(team_c_mock, team_a_mock))

        player_a = MagicMock()
        player_a.id.value = "p1"
        player_a.name = "Juande"
        player_c = MagicMock()
        player_c.id.value = "p3"
        player_c.name = "Rulo"

        container = MagicMock()
        container.get_active_meetup.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = [player_a, player_c]
        container.team_colors = ("blanco", "negro", "rojo")
        container.team_hex_bg = ("#e4e4e7", "#27272a", "#b91c1c")
        container.team_hex_text = ("#27272a", "#e4e4e7", "#fff1f2")

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")

        data = response.json()
        assert data["teamA"] == ["Rulo"]
        assert data["teamB"] == ["Juande"]
        assert data["nameA"] == "Rojo"
        assert data["nameB"] == "Blanco"
        assert data["colorA"] == "#b91c1c"
        assert data["colorB"] == "#e4e4e7"
        assert data["colorTextA"] == "#fff1f2"
        assert data["colorTextB"] == "#27272a"

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
        meetup.teams = None
        meetup.date = datetime(2026, 5, 28, 20, 0)
        meetup.location = "Polideportivo Municipal"
        meetup.locked = False
        meetup.is_signup_open.return_value = True
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
        assert data["location"] == "Polideportivo Municipal"
        assert data["players"] == [{"id": "p1", "name": "Juande"}]
        assert data["teams"] is None
        assert data["locked"] is False
        assert data["signupOpen"] is True

    @pytest.mark.asyncio
    async def test_returns_full_payload_when_teams_exist(self):
        """200 with players list and populated teams object when meetup has teams."""
        meetup = MagicMock()
        meetup.date = datetime(2026, 5, 28, 20, 0)
        meetup.location = "Polideportivo Municipal"
        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_b = MagicMock()
        pid_b.value = "p2"
        meetup.players = [pid_a, pid_b]
        meetup.teams = [MagicMock(players=[pid_a]), MagicMock(players=[pid_b])]
        meetup.locked = True
        meetup.matches = []
        meetup.is_signup_open.return_value = False

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
        container.match_link_builder.return_value.build.return_value = "http://test/match"

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/meetup/active")

        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "Polideportivo Municipal"
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
        assert data["locked"] is True
        assert data["signupOpen"] is False
        assert teams["hasRecordedResults"] is False

    @pytest.mark.asyncio
    async def test_uses_match_token_url_when_configured(self):
        """matchUrl is built by StartNextRound.execute(), which now returns the token URL."""
        meetup = MagicMock()
        meetup.date = datetime(2026, 5, 28, 20, 0)
        pid = MagicMock()
        pid.value = "p1"
        meetup.players = [pid]
        meetup.teams = [MagicMock(players=[pid]), MagicMock(players=[])]
        meetup.locked = False
        meetup.matches = []

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
        container.match_link_builder.return_value.build.return_value = (
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
        team_a_mock = MagicMock(players=[pid_a])
        team_b_mock = MagicMock(players=[pid_b])

        match = MagicMock()
        match.result.events = (ev,)
        match.teams_playing = (team_a_mock, team_b_mock)

        meetup = MagicMock()
        meetup.is_closed.return_value = True
        meetup.date = datetime(2026, 5, 28, 20, 0)
        meetup.teams = [team_a_mock, team_b_mock]
        meetup.matches = [match]
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
    async def test_colors_follow_each_teams_own_position_for_triangular(self):
        """Regression test: the last round's colors must match each team's own

        identity, not always "Blanco"/"Negro", when it's not teams 0/1 that played.
        """
        ev = MagicMock()
        ev.scorer_id.value = "p3"
        ev.assistant_id = None
        ev.team = "A"
        ev.timestamp.strftime.return_value = "20:15"

        pid_a = MagicMock()
        pid_a.value = "p1"
        pid_c = MagicMock()
        pid_c.value = "p3"

        team_a_mock = MagicMock(players=[pid_a])
        team_b_mock = MagicMock(players=[MagicMock(value="p2")])
        team_c_mock = MagicMock(players=[pid_c])

        match = MagicMock()
        match.result.events = (ev,)
        match.teams_playing = (team_c_mock, team_a_mock)

        meetup = MagicMock()
        meetup.is_closed.return_value = True
        meetup.date = datetime(2026, 5, 28, 20, 0)
        meetup.teams = [team_a_mock, team_b_mock, team_c_mock]
        meetup.matches = [match]

        player_a = MagicMock()
        player_a.id.value = "p1"
        player_a.name = "Dani"
        player_c = MagicMock()
        player_c.id.value = "p3"
        player_c.name = "Nico"

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.player_repository.find_all.return_value = [player_a, player_c]
        container.team_colors = ("blanco", "negro", "rojo")
        container.team_hex_bg = ("#e4e4e7", "#27272a", "#b91c1c")
        container.team_hex_text = ("#27272a", "#e4e4e7", "#fff1f2")

        app = create_app(container, _StubNotifier())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/2026-05-28T20:00/events")

        data = response.json()
        assert data["teamA"] == ["Nico"]
        assert data["teamB"] == ["Dani"]
        assert data["nameA"] == "Rojo"
        assert data["nameB"] == "Blanco"
        assert data["colorA"] == "#b91c1c"
        assert data["colorB"] == "#e4e4e7"

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
        meetup.matches = [MagicMock(result=MagicMock(score_a=0, score_b=0))]

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
        assert len(notifier.edited) == 1

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

        assert len(notifier.edited) == 0

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

    @pytest.mark.asyncio
    async def test_edit_match_calls_on_match_edited_not_closed(self):
        """POST /api/match/{date}/edit fires on_match_edited with the updated meetup."""
        container = MagicMock()
        closed = MagicMock()
        closed.is_closed.return_value = True
        container.meetup_repository.find_by_datetime.return_value = closed
        updated = MagicMock()
        updated.matches = [MagicMock(result=MagicMock(score_a=3, score_b=2))]
        container.edit_match_result.return_value.execute.return_value = updated
        app, notifier = _make_app(container)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/match/2026-04-30T20:00/edit", json=_VALID_BODY)

        assert response.status_code == 200
        assert notifier.edited == [updated]
        assert notifier.closed == []


class TestManifests:
    """Tests for GET /manifest-match.json and GET /manifest-manage.json."""

    def _make_named_app(self, name: str = "Tensores"):
        container = MagicMock()
        container.name = name
        container.theme_color = "#0f172a"
        container.icons_dir = ""
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
        container.set_meetup_players.return_value.execute.return_value = meetup
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
    async def test_create_meetup_response_includes_location(self):
        """POST /api/meetup/create includes the meetup's location in the response."""
        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque Central")

        container = MagicMock()
        container.set_meetup_players.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = []

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 200
        assert resp.json()["location"] == "Parque Central"

    @pytest.mark.asyncio
    async def test_create_meetup_calls_on_meetup_created_when_new(self):
        """POST /api/meetup/create fires on_meetup_created when no meetup existed at that date."""
        from pyball.domain.meetup.models import Meetup, PlayerId

        date = datetime(2026, 6, 8, 20, 0)
        meetup = Meetup.create(date=date, location="Parque")
        p_id = PlayerId.generate()
        meetup.add_player(p_id)

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = None
        container.set_meetup_players.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = []

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": [str(p_id.value)]},
            )

        assert resp.status_code == 200
        assert notifier.created == [meetup]
        assert notifier.updated == []

    @pytest.mark.asyncio
    async def test_create_meetup_calls_on_meetup_updated_when_existing(self):
        """POST /api/meetup/create fires on_meetup_updated when a meetup already existed."""
        from pyball.domain.meetup.models import Meetup

        date = datetime(2026, 6, 8, 20, 0)
        existing = Meetup.create(date=date, location="Parque")
        reset_meetup = Meetup.create(date=date, location="Parque")

        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.set_meetup_players.return_value.execute.return_value = reset_meetup
        container.player_repository.find_all.return_value = []

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 200
        assert notifier.updated == [reset_meetup]
        assert notifier.created == []

    @pytest.mark.asyncio
    async def test_create_meetup_resets_existing_meetup(self):
        """POST /api/meetup/create clears players/teams on an existing open meetup via use case."""
        from pyball.domain.meetup.models import Meetup

        date = datetime(2026, 6, 8, 20, 0)
        reset_meetup = Meetup.create(date=date, location="Parque Central")

        container = MagicMock()
        container.set_meetup_players.return_value.execute.return_value = reset_meetup
        container.player_repository.find_all.return_value = []

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 200
        assert resp.json()["teams"] is None

    @pytest.mark.asyncio
    async def test_create_meetup_409_when_match_already_finished(self):
        """POST /api/meetup/create returns 409 if the existing meetup is closed."""
        container = MagicMock()
        container.set_meetup_players.return_value.execute.side_effect = MeetupAlreadyClosedError(
            "closed"
        )

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

    @pytest.mark.asyncio
    async def test_create_meetup_422_on_invalid_player_id(self):
        """POST /api/meetup/create returns 422 when a player ID is malformed."""
        container = MagicMock()
        container.set_meetup_players.return_value.execute.side_effect = InvalidPlayerIdError(
            "bad-id"
        )

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": ["bad-id"]},
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
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response"
        ) as mock_build:
            mock_build.return_value = expected
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/generate-teams",
                    json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
                )

        assert resp.status_code == 200
        container.create_teams.assert_called_once_with("balanceado")
        mock_build.assert_called_once_with(container)

    @pytest.mark.asyncio
    async def test_generate_teams_defaults_team_count_to_two(self):
        """POST /api/meetup/generate-teams without team_count passes 2 to execute()."""
        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = meetup

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert resp.status_code == 200
        container.create_teams.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0), 2
        )

    @pytest.mark.asyncio
    async def test_generate_teams_passes_team_count_through(self):
        """POST /api/meetup/generate-teams with team_count=3 passes 3 to execute()."""
        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = meetup

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado", "team_count": 3},
            )

        assert resp.status_code == 200
        container.create_teams.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0), 3
        )

    @pytest.mark.asyncio
    async def test_generate_teams_409_when_locked(self):
        """POST /api/meetup/generate-teams returns 409 when the meetup is locked."""
        from pyball.domain.meetup.errors import MeetupLockedError

        container = MagicMock()
        meetup = MagicMock()
        meetup.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = meetup
        container.create_teams.return_value.execute.side_effect = MeetupLockedError("locked")

        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_meetup_409_when_closed():
    """/api/meetup/create maps MeetupAlreadyClosedError to 409."""
    container = MagicMock()
    container.set_meetup_players.return_value.execute.side_effect = MeetupAlreadyClosedError(
        "closed"
    )
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/meetup/create", json={"date": "2026-06-17T20:00", "player_ids": []}
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_meetup_409_when_locked():
    """/api/meetup/create maps MeetupLockedError to 409."""
    from pyball.domain.meetup.errors import MeetupLockedError

    container = MagicMock()
    container.set_meetup_players.return_value.execute.side_effect = MeetupLockedError("locked")
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/meetup/create", json={"date": "2026-06-17T20:00", "player_ids": []}
        )

    assert response.status_code == 409


# ── Golden-master route contract tests ────────────────────────────────────────


def _container_for_responses():
    """MagicMock container with realistic color/name attributes."""
    container = MagicMock()
    container.team_colors = ("blanco", "negro")
    container.team_emojis = ("⚪", "⚫")
    container.team_hex_bg = ("#e4e4e7", "#27272a")
    container.team_hex_text = ("#27272a", "#e4e4e7")
    container.name = "tensores"
    container.match_link_builder.return_value.build.return_value = "http://x/match?token=t"
    return container


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET / returns status: ok."""
    app, _ = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_match_active_404_when_no_meetup():
    """GET /api/match/active returns 404 when no active meetup."""
    container = _container_for_responses()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("none")
    app, _ = _make_app(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/match/active")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_players_endpoint_serialises_players():
    """GET /api/players returns id, name, group, and position for each player."""
    container = _container_for_responses()
    player = Player.create("Luis", group="regular", position="portero")
    container.player_repository.find_all.return_value = [player]
    app, _ = _make_app(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/players")
    assert response.json() == [
        {"id": str(player.id.value), "name": "Luis", "group": "regular", "position": "portero"}
    ]


@pytest.mark.asyncio
async def test_meetup_active_with_teams_response_shape():
    """GET /api/meetup/active returns the expected shape with team data."""
    container = _container_for_responses()
    ana, bea = Player.create("Ana"), Player.create("Bea")
    container.player_repository.find_all.return_value = [ana, bea]
    meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="X")
    meetup.add_player(ana.id)
    meetup.add_player(bea.id)
    meetup.set_teams([Team.create("A", [ana.id]), Team.create("B", [bea.id])])
    container.get_active_meetup.return_value.execute.return_value = meetup
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/meetup/active")

    body = response.json()
    assert body["date"] == "2026-06-17T20:00"
    assert body["location"] == "X"
    assert [p["name"] for p in body["players"]] == ["Ana", "Bea"]
    assert body["teams"]["teamA"] == ["Ana"]
    assert body["teams"]["teamB"] == ["Bea"]
    assert body["teams"]["nameA"] == "Blanco"
    assert body["teams"]["matchUrl"] == "http://x/match?token=t"


@pytest.mark.asyncio
async def test_meetup_active_response_includes_goalkeeper_ids():
    """GET /api/meetup/active exposes each team's goalkeeper as a player id."""
    container = _container_for_responses()
    ana, bea = Player.create("Ana"), Player.create("Bea")
    container.player_repository.find_all.return_value = [ana, bea]
    meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="X")
    meetup.add_player(ana.id)
    meetup.add_player(bea.id)
    meetup.set_teams([Team.create("A", [ana.id], goalkeeper=ana.id), Team.create("B", [bea.id])])
    container.get_active_meetup.return_value.execute.return_value = meetup
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/meetup/active")

    teams = response.json()["teams"]
    assert teams["goalkeeperA"] == str(ana.id.value)
    assert teams["goalkeeperB"] is None


@pytest.mark.asyncio
async def test_active_match_response_reflects_the_current_pending_round():
    """For a triangular with 2 finished rounds, /api/match/active shows round 3's pairing."""
    container = _container_for_responses()
    container.team_colors = ("blanco", "negro", "rojo")
    container.team_hex_bg = ("#e4e4e7", "#27272a", "#b91c1c")
    container.team_hex_text = ("#27272a", "#e4e4e7", "#fff1f2")
    ana, bea, cara = Player.create("Ana"), Player.create("Bea"), Player.create("Cara")
    container.player_repository.find_all.return_value = [ana, bea, cara]

    team_a = Team.create("A", [ana.id])
    team_b = Team.create("B", [bea.id])
    team_c = Team.create("C", [cara.id])

    meetup = Meetup.create(date=datetime(2026, 6, 20, 20, 0), location="X")
    meetup.add_player(ana.id)
    meetup.add_player(bea.id)
    meetup.add_player(cara.id)
    meetup.set_teams([team_a, team_b, team_c])

    finished_result = MatchResult(score_a=1, score_b=0, events=())
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=finished_result))
    meetup.add_match(Match(teams_playing=(team_b, team_c), result=finished_result))
    meetup.add_match(Match(teams_playing=(team_c, team_a)))  # round 3 is pending

    container.get_active_meetup.return_value.execute.return_value = meetup
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/match/active")

    assert response.status_code == 200
    data = response.json()
    # The pending match pairs team C against team A — not meetup.teams[0]/[1] (A vs B).
    assert data["teamA"] == ["Cara"]
    assert data["teamB"] == ["Ana"]
    # Each team keeps its own configured color: C is "Rojo", not "Blanco"/"Negro".
    assert data["nameA"] == "Rojo"
    assert data["nameB"] == "Blanco"
    assert data["colorA"] == "#b91c1c"
    assert data["colorB"] == "#e4e4e7"


@pytest.mark.asyncio
async def test_meetup_active_response_includes_third_team_for_triangular():
    """build_meetup_active_response includes teamC/nameC/etc. when there are 3 teams."""
    container = _container_for_responses()
    container.team_colors = ("blanco", "negro", "rojo")
    container.team_emojis = ("⚪", "⚫", "🔴")
    container.team_hex_bg = ("#e4e4e7", "#27272a", "#ef4444")
    container.team_hex_text = ("#27272a", "#e4e4e7", "#ffffff")

    ana, bea, cara = Player.create("Ana"), Player.create("Bea"), Player.create("Cara")
    container.player_repository.find_all.return_value = [ana, bea, cara]

    meetup = Meetup.create(date=datetime(2026, 6, 21, 20, 0), location="X")
    meetup.add_player(ana.id)
    meetup.add_player(bea.id)
    meetup.add_player(cara.id)
    meetup.set_teams(
        [Team.create("A", [ana.id]), Team.create("B", [bea.id]), Team.create("C", [cara.id])]
    )
    container.get_active_meetup.return_value.execute.return_value = meetup
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/meetup/active")

    teams = response.json()["teams"]
    assert teams["teamA"] == ["Ana"]
    assert teams["teamB"] == ["Bea"]
    assert teams["teamC"] == ["Cara"]
    assert teams["nameC"] == "Rojo"
    assert teams["emojiC"] == "🔴"
    assert teams["colorC"] == "#ef4444"
    assert teams["colorTextC"] == "#ffffff"


@pytest.mark.asyncio
async def test_meetup_active_response_omits_third_team_for_classic():
    """Classic 2-team meetups keep the exact same response shape as before (no teamC key)."""
    container = _container_for_responses()
    ana, bea = Player.create("Ana"), Player.create("Bea")
    container.player_repository.find_all.return_value = [ana, bea]

    meetup = Meetup.create(date=datetime(2026, 6, 22, 20, 0), location="X")
    meetup.add_player(ana.id)
    meetup.add_player(bea.id)
    meetup.set_teams([Team.create("A", [ana.id]), Team.create("B", [bea.id])])
    container.get_active_meetup.return_value.execute.return_value = meetup
    app, _ = _make_app(container)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/meetup/active")

    teams = response.json()["teams"]
    assert "teamC" not in teams


@pytest.mark.asyncio
async def test_meetup_create_422_on_bad_date():
    """POST /api/meetup/create with invalid date returns 422."""
    app, _ = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/meetup/create", json={"date": "not-a-date", "player_ids": []}
        )
    assert response.status_code == 422


class TestMeetupHistory:
    """Tests for GET /api/meetup/history."""

    @pytest.mark.asyncio
    async def test_returns_only_closed_meetups_newest_first(self):
        """Only closed meetups are returned, sorted by date descending."""
        open_meetup = Meetup.create(date=datetime(2026, 7, 20, 20, 0), location="Abierto")

        p1 = PlayerId.generate()
        closed_old = Meetup.create(date=datetime(2026, 6, 1, 20, 0), location="Viejo")
        closed_old.add_player(p1)
        team_a = Team.create("A", [p1])
        team_b = Team.create("B", [])
        closed_old.set_teams([team_a, team_b])
        closed_old.add_match(Match(teams_playing=(team_a, team_b)))
        closed_old.record_result(MatchResult(score_a=1, score_b=0, events=()))
        closed_old.close()

        closed_new = Meetup.create(date=datetime(2026, 7, 1, 20, 0), location="Nuevo")
        closed_new.add_player(p1)
        closed_new.set_teams([team_a, team_b])
        closed_new.add_match(Match(teams_playing=(team_a, team_b)))
        closed_new.record_result(MatchResult(score_a=2, score_b=2, events=()))
        closed_new.close()

        container = MagicMock()
        container.meetup_repository.find_all.return_value = [open_meetup, closed_old, closed_new]
        app, _ = _make_app(container=container)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/meetup/history")

        assert resp.status_code == 200
        assert resp.json() == [
            {"date": "2026-07-01T20:00", "location": "Nuevo"},
            {"date": "2026-06-01T20:00", "location": "Viejo"},
        ]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_closed_meetups(self):
        """Returns an empty list (not 404) when nothing is closed yet."""
        container = MagicMock()
        container.meetup_repository.find_all.return_value = []
        app, _ = _make_app(container=container)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/meetup/history")

        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_match_token_gets_403_on_manage_and_200_on_public():
    """A match-token holder cannot open /manage but can read /sw.js."""
    app = create_app(
        MagicMock(), _StubNotifier(), match_token="match-tok", manage_token="manage-tok"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.cookies.set("pyball_match_token", "match-tok")
        manage = await client.get("/manage")
        sw = await client.get("/sw.js")
    assert manage.status_code == 403
    assert sw.status_code == 200


@pytest.mark.asyncio
async def test_sw_js_embeds_package_version():
    """/sw.js substitutes __VERSION__ so each release invalidates the PWA cache."""
    app, _ = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sw.js")
    assert response.status_code == 200
    assert "__VERSION__" not in response.text
    assert "pyball-" in response.text


@pytest.mark.asyncio
async def test_manifest_uses_instance_theme_color():
    """manifest-match.json uses the container's theme_color."""
    container = _container_for_responses()
    container.theme_color = "#112233"
    app, _ = _make_app(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/manifest-match.json")
    body = response.json()
    assert body["theme_color"] == "#112233"
    assert body["background_color"] == "#112233"
    assert body["name"] == "PyBall – Partido tensores"


class TestUpdateMeetupDate:
    """Tests for POST /api/meetup/date."""

    @pytest.mark.asyncio
    async def test_returns_200_with_new_date(self):
        """Successful date change returns the new date."""
        from pyball.domain.meetup.models import Meetup

        updated = Meetup.create(date=datetime(2026, 6, 15, 20, 0), location="Parque")
        container = MagicMock()
        container.update_meetup_date.return_value.execute.return_value = updated

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/date",
                json={"old_date": "2026-06-08T20:00", "new_date": "2026-06-15T20:00"},
            )

        assert resp.status_code == 200
        assert resp.json() == {"date": "2026-06-15T20:00", "location": "Parque"}
        assert notifier.date_changed == [(datetime(2026, 6, 8, 20, 0), updated)]

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self):
        """404 when no meetup exists at old_date."""
        container = MagicMock()
        container.update_meetup_date.return_value.execute.side_effect = MeetupNotFoundError(
            "2026-06-08T20:00"
        )
        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/date",
                json={"old_date": "2026-06-08T20:00", "new_date": "2026-06-15T20:00"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_409_when_new_date_taken(self):
        """409 when another meetup already exists at new_date."""
        from pyball.domain.meetup.errors import DuplicateMeetupError

        container = MagicMock()
        container.update_meetup_date.return_value.execute.side_effect = DuplicateMeetupError(
            "taken"
        )
        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/date",
                json={"old_date": "2026-06-08T20:00", "new_date": "2026-06-15T20:00"},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_returns_422_when_closed(self):
        """422 when the use case rejects a closed meetup."""
        container = MagicMock()
        container.update_meetup_date.return_value.execute.side_effect = ValueError(
            "Cannot change date of a finished match"
        )
        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/date",
                json={"old_date": "2026-06-08T20:00", "new_date": "2026-06-15T20:00"},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_422_on_bad_date_format(self):
        """422 for unparseable date strings."""
        app, _ = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/date",
                json={"old_date": "not-a-date", "new_date": "2026-06-15T20:00"},
            )
        assert resp.status_code == 422


class TestUpdateMeetupLocation:
    """Tests for POST /api/meetup/location."""

    @pytest.mark.asyncio
    async def test_returns_200_with_new_location(self):
        """Successful location change returns the new location."""
        from pyball.domain.meetup.models import Meetup

        updated = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Nuevo Campo")
        container = MagicMock()
        container.update_meetup_location.return_value.execute.return_value = updated

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/location",
                json={"date": "2026-06-08T20:00", "location": "Nuevo Campo"},
            )

        assert resp.status_code == 200
        assert resp.json() == {"date": "2026-06-08T20:00", "location": "Nuevo Campo"}
        assert notifier.updated == [updated]

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self):
        """404 when no meetup exists at date."""
        container = MagicMock()
        container.update_meetup_location.return_value.execute.side_effect = MeetupNotFoundError(
            "2026-06-08T20:00"
        )
        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/location",
                json={"date": "2026-06-08T20:00", "location": "Nuevo Campo"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_422_on_empty_location(self):
        """422 when the use case rejects an empty location."""
        container = MagicMock()
        container.update_meetup_location.return_value.execute.side_effect = ValueError(
            "Location cannot be empty"
        )
        app, _ = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/location",
                json={"date": "2026-06-08T20:00", "location": ""},
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_422_on_bad_date_format(self):
        """422 for unparseable date strings."""
        app, _ = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/location",
                json={"date": "not-a-date", "location": "X"},
            )
        assert resp.status_code == 422


class TestCreatePlayerEndpoint:
    """Tests for POST /api/players."""

    @pytest.mark.asyncio
    async def test_create_player_returns_201_with_full_shape(self):
        """POST /api/players with only a name defaults group to substitute, no position."""
        container = MagicMock()
        player = Player.create("Nuevo Fichaje", group="substitute")
        container.create_player.return_value.execute.return_value = player

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/players", json={"name": "Nuevo Fichaje"})

        assert resp.status_code == 201
        assert resp.json() == {
            "id": str(player.id.value),
            "name": "Nuevo Fichaje",
            "group": "substitute",
            "position": None,
        }
        container.create_player.return_value.execute.assert_called_once_with(
            name="Nuevo Fichaje", group="substitute", position=None
        )

    @pytest.mark.asyncio
    async def test_create_player_with_group_and_position(self):
        """POST /api/players passes explicit group and position through."""
        container = MagicMock()
        player = Player.create("Iker", group="regular", position="portero")
        container.create_player.return_value.execute.return_value = player

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/players",
                json={"name": "Iker", "group": "regular", "position": "portero"},
            )

        assert resp.status_code == 201
        assert resp.json()["position"] == "portero"
        container.create_player.return_value.execute.assert_called_once_with(
            name="Iker", group="regular", position="portero"
        )

    @pytest.mark.asyncio
    async def test_create_player_422_on_invalid_position(self):
        """POST /api/players returns 422 for an unrecognized position value."""
        container = MagicMock()
        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/players", json={"name": "Iker", "position": "lateral"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_player_422_on_invalid_group(self):
        """POST /api/players returns 422 for an unrecognized group value."""
        container = MagicMock()
        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/players", json={"name": "Iker", "group": "vip"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_player_409_on_duplicate_name(self):
        """POST /api/players returns 409 when the name already exists."""
        container = MagicMock()
        container.create_player.return_value.execute.side_effect = PlayerAlreadyExistsError(
            "Nuevo Fichaje"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/players", json={"name": "Nuevo Fichaje"})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_player_422_on_blank_name(self):
        """POST /api/players returns 422 for an empty or whitespace-only name."""
        container = MagicMock()

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/players", json={"name": "   "})

        assert resp.status_code == 422
        container.create_player.assert_not_called()


class TestEditPlayerEndpoint:
    """Tests for POST /api/players/{id}/edit."""

    @pytest.mark.asyncio
    async def test_edit_player_returns_updated_shape(self):
        """Editing a player renames it, changes group and position, and returns the result."""
        container = MagicMock()
        player = Player.create("Nuevo Nombre", group="regular", position="defensa")
        container.rename_player.return_value.execute.return_value = player
        container.change_player_group.return_value.execute.return_value = player
        container.set_player_position.return_value.execute.return_value = player

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                f"/api/players/{player.id.value}/edit",
                json={"name": "Nuevo Nombre", "group": "regular", "position": "defensa"},
            )

        assert resp.status_code == 200
        assert resp.json() == {
            "id": str(player.id.value),
            "name": "Nuevo Nombre",
            "group": "regular",
            "position": "defensa",
        }
        container.rename_player.return_value.execute.assert_called_once_with(
            str(player.id.value), "Nuevo Nombre"
        )
        container.change_player_group.return_value.execute.assert_called_once_with(
            str(player.id.value), "regular"
        )
        container.set_player_position.return_value.execute.assert_called_once_with(
            str(player.id.value), "defensa"
        )

    @pytest.mark.asyncio
    async def test_edit_player_404_when_not_found(self):
        """Editing a nonexistent player returns 404."""
        container = MagicMock()
        container.rename_player.return_value.execute.side_effect = PlayerNotFoundError("bad-id")

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/players/bad-id/edit",
                json={"name": "X", "group": "regular"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_player_409_on_name_taken(self):
        """Editing a player to a name already used by someone else returns 409."""
        container = MagicMock()
        container.rename_player.return_value.execute.side_effect = NameAlreadyTakenError("X")

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/players/11111111-1111-4111-8111-111111111111/edit",
                json={"name": "X", "group": "regular"},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_edit_player_422_on_invalid_position(self):
        """Editing a player with an unrecognized position returns 422."""
        container = MagicMock()
        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/players/11111111-1111-4111-8111-111111111111/edit",
                json={"name": "X", "group": "regular", "position": "lateral"},
            )
        assert resp.status_code == 422
        container.rename_player.assert_not_called()


class TestDeletePlayerEndpoint:
    """Tests for DELETE /api/players/{id}."""

    @pytest.mark.asyncio
    async def test_delete_player_returns_200(self):
        """Deleting an existing player returns a status confirmation."""
        container = MagicMock()
        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/players/11111111-1111-4111-8111-111111111111")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        container.delete_player.return_value.execute.assert_called_once_with(
            "11111111-1111-4111-8111-111111111111"
        )

    @pytest.mark.asyncio
    async def test_delete_player_404_when_not_found(self):
        """Deleting a nonexistent player returns 404."""
        container = MagicMock()
        container.delete_player.return_value.execute.side_effect = PlayerNotFoundError("bad-id")
        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/players/bad-id")
        assert resp.status_code == 404


class TestCancelMeetupEndpoint:
    """Tests for DELETE /api/meetup/active."""

    @pytest.mark.asyncio
    async def test_cancel_returns_200_with_status_and_date(self):
        """DELETE /api/meetup/active deletes the active meetup and reports its date."""
        meetup = MagicMock()
        meetup.date = datetime(2026, 6, 17, 20, 0)
        container = MagicMock()
        container.cancel_meetup.return_value.execute.return_value = meetup

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/meetup/active")

        assert resp.status_code == 200
        assert resp.json() == {"status": "cancelled", "date": "2026-06-17T20:00"}
        container.cancel_meetup.return_value.execute.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_cancel_404_when_no_active_meetup(self):
        """DELETE /api/meetup/active returns 404 when there is no active meetup."""
        container = MagicMock()
        container.cancel_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/meetup/active")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_409_when_locked(self):
        """DELETE /api/meetup/active returns 409 when the active meetup is locked."""
        from pyball.domain.meetup.errors import MeetupLockedError

        container = MagicMock()
        container.cancel_meetup.return_value.execute.side_effect = MeetupLockedError("locked")

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/meetup/active")

        assert resp.status_code == 409


class TestLockMeetupEndpoint:
    """Tests for POST /api/meetup/lock."""

    @pytest.mark.asyncio
    async def test_lock_returns_active_meetup_response(self):
        """POST /api/meetup/lock locks the meetup and returns the active meetup payload."""
        from unittest.mock import patch

        container = MagicMock()
        expected = {"date": "2026-06-08T20:00", "players": [], "teams": None, "locked": True}

        app, _ = _make_app(container)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value=expected,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/meetup/lock", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 200
        assert resp.json() == expected
        container.lock_meetup.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0)
        )

    @pytest.mark.asyncio
    async def test_lock_404_when_meetup_not_found(self):
        """POST /api/meetup/lock returns 404 when LockMeetup raises MeetupNotFoundError."""
        container = MagicMock()
        container.lock_meetup.return_value.execute.side_effect = MeetupNotFoundError(
            "2026-06-08T20:00"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/lock", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_lock_409_when_no_teams(self):
        """POST /api/meetup/lock returns 409 when LockMeetup raises MeetupHasNoTeamsError."""
        container = MagicMock()
        container.lock_meetup.return_value.execute.side_effect = MeetupHasNoTeamsError("no teams")

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/lock", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_lock_422_on_bad_date(self):
        """POST /api/meetup/lock returns 422 for unparseable date strings."""
        app, _ = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/lock", json={"date": "not-a-date"})

        assert resp.status_code == 422


class TestDestroyTeamsEndpoint:
    """Tests for POST /api/meetup/destroy-teams."""

    @pytest.mark.asyncio
    async def test_destroy_teams_calls_notifier_and_returns_active_meetup_response(self):
        """POST /api/meetup/destroy-teams destroys teams, notifies, and returns the payload."""
        from unittest.mock import patch

        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        container = MagicMock()
        container.destroy_teams.return_value.execute.return_value = meetup
        expected = {"date": "2026-06-08T20:00", "players": [], "teams": None, "locked": False}

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value=expected,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/meetup/destroy-teams", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 200
        assert resp.json() == expected
        assert notifier.updated == [meetup]

    @pytest.mark.asyncio
    async def test_destroy_teams_404_when_meetup_not_found(self):
        """POST /api/meetup/destroy-teams returns 404 when the meetup doesn't exist."""
        container = MagicMock()
        container.destroy_teams.return_value.execute.side_effect = MeetupNotFoundError(
            "2026-06-08T20:00"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/destroy-teams", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_destroy_teams_409_when_no_teams(self):
        """POST /api/meetup/destroy-teams returns 409 when there are no teams to destroy."""
        container = MagicMock()
        container.destroy_teams.return_value.execute.side_effect = MeetupHasNoTeamsError(
            "no teams"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/destroy-teams", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_destroy_teams_409_when_results_already_recorded(self):
        """POST /api/meetup/destroy-teams returns 409 when a match already has a result."""
        from pyball.domain.meetup.errors import MeetupHasRecordedResultsError

        container = MagicMock()
        container.destroy_teams.return_value.execute.side_effect = MeetupHasRecordedResultsError(
            "has results"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/destroy-teams", json={"date": "2026-06-08T20:00"})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_destroy_teams_does_not_call_notifier_on_error(self):
        """POST /api/meetup/destroy-teams does not notify when the use case raises."""
        container = MagicMock()
        container.destroy_teams.return_value.execute.side_effect = MeetupHasNoTeamsError(
            "no teams"
        )

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/api/meetup/destroy-teams", json={"date": "2026-06-08T20:00"})

        assert notifier.updated == []


class TestCloseMeetupEndpoint:
    """Tests for POST /api/meetup/close."""

    @pytest.mark.asyncio
    async def test_close_returns_200_with_status_and_date(self):
        """POST /api/meetup/close closes the active meetup and reports its date."""
        active_meetup = MagicMock()
        active_meetup.date = datetime(2026, 7, 8, 20, 0)
        closed_meetup = MagicMock()
        closed_meetup.date = datetime(2026, 7, 8, 20, 0)
        container = MagicMock()
        container.get_active_meetup.return_value.execute.return_value = active_meetup
        container.close_meetup.return_value.execute.return_value = closed_meetup

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/close")

        assert resp.status_code == 200
        assert resp.json() == {"status": "closed", "date": "2026-07-08T20:00"}
        container.close_meetup.return_value.execute.assert_called_once_with(active_meetup.date)

    @pytest.mark.asyncio
    async def test_close_404_when_no_active_meetup(self):
        """POST /api/meetup/close returns 404 when there is no active meetup."""
        container = MagicMock()
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError(
            "active"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/close")

        assert resp.status_code == 404
        container.close_meetup.return_value.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_409_when_already_closed(self):
        """POST /api/meetup/close returns 409 if the meetup got closed concurrently."""
        active_meetup = MagicMock()
        active_meetup.date = datetime(2026, 7, 8, 20, 0)
        container = MagicMock()
        container.get_active_meetup.return_value.execute.return_value = active_meetup
        container.close_meetup.return_value.execute.side_effect = MeetupAlreadyClosedError(
            "closed"
        )

        app, _ = _make_app(container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/close")

        assert resp.status_code == 409


class TestMeetupRouteNotifierCalls:
    """Notifier is called correctly for all meetup-mutating HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_create_meetup_calls_on_meetup_updated_on_success(self):
        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        container = MagicMock()
        container.set_meetup_players.return_value.execute.return_value = meetup
        container.player_repository.find_all.return_value = []

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert resp.status_code == 200
        assert notifier.updated == [meetup]

    @pytest.mark.asyncio
    async def test_create_meetup_does_not_call_notifier_on_error(self):
        container = MagicMock()
        container.set_meetup_players.return_value.execute.side_effect = MeetupAlreadyClosedError(
            "closed"
        )

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                "/api/meetup/create",
                json={"date": "2026-06-08T20:00", "player_ids": []},
            )

        assert notifier.updated == []

    @pytest.mark.asyncio
    async def test_generate_teams_calls_on_meetup_updated_on_success(self):
        from unittest.mock import patch

        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        container = MagicMock()
        existing = MagicMock()
        existing.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = existing
        container.create_teams.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value={"date": "2026-06-08T20:00", "players": [], "teams": None},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/generate-teams",
                    json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
                )

        assert resp.status_code == 200
        assert notifier.updated == [meetup]

    @pytest.mark.asyncio
    async def test_generate_teams_does_not_call_notifier_on_error(self):
        container = MagicMock()
        existing = MagicMock()
        existing.is_closed.return_value = False
        container.meetup_repository.find_by_datetime.return_value = existing
        container.create_teams.return_value.execute.side_effect = ValueError(
            "Need at least 2 players"
        )

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                "/api/meetup/generate-teams",
                json={"date": "2026-06-08T20:00", "algorithm": "balanceado"},
            )

        assert notifier.updated == []

    @pytest.mark.asyncio
    async def test_assign_teams_calls_on_meetup_updated_on_success(self):
        from unittest.mock import patch

        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        existing = MagicMock()
        existing.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.assign_teams_by_id.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value={"date": "2026-06-08T20:00", "players": [], "teams": None},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/assign-teams",
                    json={"date": "2026-06-08T20:00", "team_a_ids": [], "team_b_ids": []},
                )

        assert resp.status_code == 200
        assert notifier.updated == [meetup]

    @pytest.mark.asyncio
    async def test_assign_teams_does_not_call_notifier_on_error(self):
        existing = MagicMock()
        existing.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.assign_teams_by_id.return_value.execute.side_effect = ValueError("bad ids")

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                "/api/meetup/assign-teams",
                json={"date": "2026-06-08T20:00", "team_a_ids": [], "team_b_ids": []},
            )

        assert notifier.updated == []

    @pytest.mark.asyncio
    async def test_assign_teams_passes_team_c_ids_through(self):
        """POST /api/meetup/assign-teams with team_c_ids forwards it to execute()."""
        from unittest.mock import patch

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        existing = MagicMock()
        existing.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.assign_teams_by_id.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value={"date": "2026-06-08T20:00", "players": [], "teams": None},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/assign-teams",
                    json={
                        "date": "2026-06-08T20:00",
                        "team_a_ids": ["id-a"],
                        "team_b_ids": ["id-b"],
                        "team_c_ids": ["id-c"],
                    },
                )

        assert resp.status_code == 200
        container.assign_teams_by_id.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0), ["id-a"], ["id-b"], ["id-c"], None, None, None
        )

    @pytest.mark.asyncio
    async def test_assign_teams_passes_none_when_team_c_ids_omitted(self):
        """POST /api/meetup/assign-teams without team_c_ids passes None to execute()."""
        from unittest.mock import patch

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        existing = MagicMock()
        existing.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.assign_teams_by_id.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value={"date": "2026-06-08T20:00", "players": [], "teams": None},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/assign-teams",
                    json={"date": "2026-06-08T20:00", "team_a_ids": [], "team_b_ids": []},
                )

        assert resp.status_code == 200
        container.assign_teams_by_id.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0), [], [], None, None, None, None
        )

    @pytest.mark.asyncio
    async def test_assign_teams_passes_goalkeeper_ids_through(self):
        """POST /api/meetup/assign-teams forwards goalkeeper_*_id to the use case."""
        from unittest.mock import patch

        meetup = Meetup.create(date=datetime(2026, 6, 8, 20, 0), location="Parque")
        existing = MagicMock()
        existing.is_closed.return_value = False
        container = MagicMock()
        container.meetup_repository.find_by_datetime.return_value = existing
        container.assign_teams_by_id.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        with patch(
            "pyball.infrastructure.http.routes.meetup.build_meetup_active_response",
            return_value={"date": "2026-06-08T20:00", "players": [], "teams": None},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    "/api/meetup/assign-teams",
                    json={
                        "date": "2026-06-08T20:00",
                        "team_a_ids": ["id-a"],
                        "team_b_ids": ["id-b"],
                        "team_a_goalkeeper_id": "id-a",
                    },
                )

        assert resp.status_code == 200
        container.assign_teams_by_id.return_value.execute.assert_called_once_with(
            datetime(2026, 6, 8, 20, 0), ["id-a"], ["id-b"], None, "id-a", None, None
        )

    @pytest.mark.asyncio
    async def test_cancel_meetup_calls_on_meetup_cancelled_on_success(self):
        meetup = MagicMock()
        meetup.date = datetime(2026, 6, 17, 20, 0)
        container = MagicMock()
        container.cancel_meetup.return_value.execute.return_value = meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/meetup/active")

        assert resp.status_code == 200
        assert notifier.cancelled == [meetup]

    @pytest.mark.asyncio
    async def test_cancel_meetup_does_not_call_notifier_on_404(self):
        container = MagicMock()
        container.cancel_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.delete("/api/meetup/active")

        assert notifier.cancelled == []

    @pytest.mark.asyncio
    async def test_close_meetup_calls_on_match_closed_on_success(self):
        active_meetup = MagicMock()
        active_meetup.date = datetime(2026, 7, 8, 20, 0)
        closed_meetup = MagicMock()
        closed_meetup.date = datetime(2026, 7, 8, 20, 0)
        container = MagicMock()
        container.get_active_meetup.return_value.execute.return_value = active_meetup
        container.close_meetup.return_value.execute.return_value = closed_meetup

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/close")

        assert resp.status_code == 200
        assert notifier.closed == [closed_meetup]

    @pytest.mark.asyncio
    async def test_close_meetup_does_not_call_notifier_on_404(self):
        container = MagicMock()
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError(
            "active"
        )

        notifier = _StubNotifier()
        app = create_app(container, notifier)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/api/meetup/close")

        assert notifier.closed == []


class TestCreateNextMeetup:
    """Tests for POST /api/meetup/create-next."""

    @pytest.mark.asyncio
    async def test_returns_200_and_calls_on_meetup_created(self):
        """Creates an empty meetup at the computed date and fires on_meetup_created."""
        from pyball.domain.meetup.models import Meetup

        meetup = Meetup.create(date=datetime(2026, 6, 10, 20, 0), location="Parque Central")
        container = MagicMock()
        container.default_week_day = "wednesday"
        container.default_hour = "20:00"
        container.create_meetup.return_value.execute.return_value = meetup

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/create-next")

        assert resp.status_code == 200
        assert resp.json() == {
            "date": "2026-06-10T20:00",
            "players": [],
            "teams": None,
            "location": "Parque Central",
        }
        assert notifier.created == [meetup]

    @pytest.mark.asyncio
    async def test_returns_409_when_meetup_already_exists_at_computed_date(self):
        """409 when a meetup (open or closed) already exists at the computed date."""
        from pyball.domain.meetup.errors import DuplicateMeetupError

        container = MagicMock()
        container.default_week_day = "wednesday"
        container.default_hour = "20:00"
        container.create_meetup.return_value.execute.side_effect = DuplicateMeetupError("taken")

        app, notifier = _make_app(container=container)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/meetup/create-next")

        assert resp.status_code == 409
        assert notifier.created == []
