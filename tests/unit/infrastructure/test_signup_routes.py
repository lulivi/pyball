"""Tests for /api/signup/* routes."""

import hashlib
import hmac
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.errors import MeetupNotFoundError, SignupClosedError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player
from pyball.infrastructure.http.app import create_app
from pyball.infrastructure.signup.code_store import SignupCodeStore

SIGNUP_TOKEN = "signup-tok"


def _identity_cookie(player_id: str) -> str:
    mac = hmac.new(SIGNUP_TOKEN.encode(), player_id.encode(), hashlib.sha256).hexdigest()
    return f"{player_id}.{mac}"


def _client(app) -> AsyncClient:
    # Passing signup_token to create_app also activates TokenAuthMiddleware (Task 2),
    # which gates /api/signup/* behind a site-level "signup" scope credential —
    # the pyball_signup_token cookie — separate from the per-player identity cookie
    # (pyball_signup_player) under test here. Preset it so requests reach the route
    # handlers, where the actual behaviour under test is exercised.
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    client.cookies.set("pyball_signup_token", SIGNUP_TOKEN)
    return client


def _container_with_code_store(tmp_path, player: Player, code: str = "ABCD2345"):
    # _code_store() in routes/signup.py resolves to data_dir / "signup" / "codes.json" —
    # this fixture must write to that same path for verify_code() to find it.
    store = SignupCodeStore(tmp_path / "signup" / "codes.json")
    store.set_code(str(player.id.value), code)
    container = MagicMock()
    container.data_dir = tmp_path
    container.team_colors = ("blanco", "negro", "rojo")
    container.team_hex_bg = ("#e4e4e7", "#27272a", "#b91c1c")
    container.team_hex_text = ("#27272a", "#e4e4e7", "#fff1f2")
    container.player_repository.find_by_id.return_value = player
    container.player_repository.find_all.return_value = [player]
    return container


def _make_app(container):
    return create_app(
        container,
        AsyncMock(spec=MatchNotifier),
        signup_token=SIGNUP_TOKEN,
        enable_web_signup=True,
    )


class TestVerifyCode:
    """Tests for POST /api/signup/verify."""

    @pytest.mark.asyncio
    async def test_correct_code_sets_identity_cookie_and_returns_player(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.post("/api/signup/verify", json={"code": "ABCD2345"})

        assert response.status_code == 200
        assert response.json() == {"id": str(player.id.value), "name": "Ana"}
        assert "pyball_signup_player" in response.cookies

    @pytest.mark.asyncio
    async def test_wrong_code_returns_401(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.post("/api/signup/verify", json={"code": "WRONGCODE"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sets_secure_cookie_over_https(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        # Built manually (not via _client()) so the base_url can be https://, needed
        # to exercise the secure=request.url.scheme == "https" branch — but it still
        # needs the pyball_signup_token scope cookie _client() would otherwise set,
        # or TokenAuthMiddleware rejects the request before it reaches the handler.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
            c.cookies.set("pyball_signup_token", SIGNUP_TOKEN)
            response = await c.post("/api/signup/verify", json={"code": "ABCD2345"})

        set_cookie = response.headers.get("set-cookie", "")
        assert "Secure" in set_cookie


class TestGetMe:
    """Tests for GET /api/signup/me."""

    @pytest.mark.asyncio
    async def test_valid_identity_cookie_returns_player(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(player.id.value)))
            response = await c.get("/api/signup/me")

        assert response.status_code == 200
        assert response.json() == {"id": str(player.id.value), "name": "Ana"}

    @pytest.mark.asyncio
    async def test_missing_identity_cookie_returns_401(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.get("/api/signup/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_tampered_identity_cookie_returns_401(self, tmp_path):
        player = Player.create("Ana", group="regular")
        other = Player.create("Bea", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            forged = f"{other.id.value}.{_identity_cookie(str(player.id.value)).split('.')[1]}"
            c.cookies.set("pyball_signup_player", forged)
            response = await c.get("/api/signup/me")

        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/signup/logout."""

    @pytest.mark.asyncio
    async def test_clears_identity_cookie(self, tmp_path):
        player = Player.create("Ana", group="regular")
        container = _container_with_code_store(tmp_path, player)
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(player.id.value)))
            response = await c.post("/api/signup/logout")

        assert response.status_code == 200
        assert "pyball_signup_player=" in response.headers.get("set-cookie", "")


class TestSignupMeetup:
    """Tests for GET /api/signup/meetup."""

    @pytest.mark.asyncio
    async def test_returns_roster_when_signup_open(self, tmp_path):
        ana, bea = Player.create("Ana"), Player.create("Bea")
        container = _container_with_code_store(tmp_path, ana)
        container.player_repository.find_all.return_value = [ana, bea]
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        meetup.add_player(ana.id)
        container.get_active_meetup.return_value.execute.return_value = meetup
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.get("/api/signup/meetup")

        assert response.status_code == 200
        data = response.json()
        assert data["signupOpen"] is True
        assert data["isJoined"] is True
        assert data["roster"] == ["Ana"]
        assert data["teams"] is None

    @pytest.mark.asyncio
    async def test_returns_404_when_no_active_meetup(self, tmp_path):
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("none")
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.get("/api/signup/meetup")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_both_teams_with_me_highlighted_when_teams_exist(self, tmp_path):
        ana, bea, carlos = Player.create("Ana"), Player.create("Bea"), Player.create("Carlos")
        container = _container_with_code_store(tmp_path, ana)
        container.player_repository.find_all.return_value = [ana, bea, carlos]
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        meetup.add_player(ana.id)
        meetup.add_player(bea.id)
        meetup.add_player(carlos.id)
        meetup.teams = [
            Team.create("A", [ana.id, bea.id]),
            Team.create("B", [carlos.id]),
        ]
        container.get_active_meetup.return_value.execute.return_value = meetup
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.get("/api/signup/meetup")

        assert response.status_code == 200
        data = response.json()
        assert data["signupOpen"] is False
        assert data["roster"] is None
        assert data["teams"] == [
            {
                "name": "Blanco",
                "colorBg": "#e4e4e7",
                "colorText": "#27272a",
                "players": [
                    {"name": "Ana", "isMe": True},
                    {"name": "Bea", "isMe": False},
                ],
            },
            {
                "name": "Negro",
                "colorBg": "#27272a",
                "colorText": "#e4e4e7",
                "players": [{"name": "Carlos", "isMe": False}],
            },
        ]

    @pytest.mark.asyncio
    async def test_shows_both_teams_even_when_not_in_either(self, tmp_path):
        ana, bea, carlos = Player.create("Ana"), Player.create("Bea"), Player.create("Carlos")
        container = _container_with_code_store(tmp_path, ana)
        container.player_repository.find_all.return_value = [ana, bea, carlos]
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        meetup.add_player(bea.id)
        meetup.add_player(carlos.id)
        meetup.teams = [
            Team.create("A", [bea.id]),
            Team.create("B", [carlos.id]),
        ]
        container.get_active_meetup.return_value.execute.return_value = meetup
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.get("/api/signup/meetup")

        assert response.status_code == 200
        data = response.json()
        assert data["isJoined"] is False
        assert all(not p["isMe"] for team in data["teams"] for p in team["players"])
        assert [team["name"] for team in data["teams"]] == ["Blanco", "Negro"]
        assert [team["colorBg"] for team in data["teams"]] == ["#e4e4e7", "#27272a"]


class TestJoinLeave:
    """Tests for POST /api/signup/join and /api/signup/leave."""

    @pytest.mark.asyncio
    async def test_join_calls_add_player_by_id_use_case(self, tmp_path):
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        container.get_active_meetup.return_value.execute.return_value = meetup
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.post("/api/signup/join")

        assert response.status_code == 200
        container.add_player_to_meetup_by_id.return_value.execute.assert_called_once_with(
            meetup.date, ana.id
        )

    @pytest.mark.asyncio
    async def test_join_409_when_signup_closed(self, tmp_path):
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        container.get_active_meetup.return_value.execute.return_value = meetup
        container.add_player_to_meetup_by_id.return_value.execute.side_effect = SignupClosedError(
            "closed"
        )
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.post("/api/signup/join")

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_leave_calls_remove_player_by_id_use_case(self, tmp_path):
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        meetup.add_player(ana.id)
        container.get_active_meetup.return_value.execute.return_value = meetup
        app = _make_app(container)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            response = await c.post("/api/signup/leave")

        assert response.status_code == 200
        container.remove_player_from_meetup_by_id.return_value.execute.assert_called_once_with(
            meetup.date, ana.id
        )

    @pytest.mark.asyncio
    async def test_join_and_leave_notify(self, tmp_path):
        """A web join and leave are announced like Telegram ones."""
        ana = Player.create("Ana", group="substitute")
        container = _container_with_code_store(tmp_path, ana)
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        container.get_active_meetup.return_value.execute.return_value = meetup
        container.add_player_to_meetup_by_id.return_value.execute.return_value = meetup
        container.remove_player_from_meetup_by_id.return_value.execute.return_value = meetup
        notifier = AsyncMock(spec=MatchNotifier)
        app = create_app(container, notifier, signup_token=SIGNUP_TOKEN, enable_web_signup=True)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            await c.post("/api/signup/join")
            await c.post("/api/signup/leave")

        notifier.on_player_joined.assert_awaited_once_with(meetup, ana, True)
        notifier.on_player_left.assert_awaited_once_with(meetup, ana, True)

    @pytest.mark.asyncio
    async def test_join_when_already_in_notifies_nothing(self, tmp_path):
        """Joining twice changes nothing, so nothing is announced."""
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        meetup = Meetup.create(date=datetime(2026, 6, 17, 20, 0), location="Campo")
        meetup.add_player(ana.id)
        container.get_active_meetup.return_value.execute.return_value = meetup
        notifier = AsyncMock(spec=MatchNotifier)
        app = create_app(container, notifier, signup_token=SIGNUP_TOKEN, enable_web_signup=True)

        async with _client(app) as c:
            c.cookies.set("pyball_signup_player", _identity_cookie(str(ana.id.value)))
            await c.post("/api/signup/join")

        notifier.on_player_joined.assert_not_called()

    @pytest.mark.asyncio
    async def test_requires_identity(self, tmp_path):
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.post("/api/signup/join")

        assert response.status_code == 401


class TestSignupRoutesDisabledByDefault:
    """/api/signup/* must not exist unless enable_web_signup=True."""

    @pytest.mark.asyncio
    async def test_verify_returns_404_when_signup_disabled(self):
        container = MagicMock()
        app = create_app(container, AsyncMock(spec=MatchNotifier))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.post("/api/signup/verify", json={"code": "ABCD2345"})

        # Not 404: no route matches, so the request falls through to the "/" StaticFiles
        # catch-all mount, which rejects non-GET/HEAD methods with 405 before ever
        # looking at the path (see starlette.staticfiles.StaticFiles.get_response) —
        # this is pre-existing behaviour of create_app's static mount, unrelated to
        # the signup feature. The important assertion is that the signup route itself
        # was never registered.
        assert response.status_code == 405


class TestSignupPage:
    """Tests for GET /signup and static asset isolation."""

    @pytest.mark.asyncio
    async def test_signup_page_served_when_enabled(self, tmp_path):
        # Uses _client(), not a bare AsyncClient: TokenAuthMiddleware (Task 2) already
        # gates /signup behind the "signup" scope cookie, same as /api/signup/* — see
        # the comment on _client() above.
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.get("/signup")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_signup_page_404_when_disabled(self):
        container = MagicMock()
        app = create_app(container, AsyncMock(spec=MatchNotifier))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/signup")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_signup_static_js_served_when_enabled(self, tmp_path):
        # Same reasoning as above: /signup-static/* requires the "signup" scope cookie
        # when signup_token is configured, so this needs _client() too.
        ana = Player.create("Ana")
        container = _container_with_code_store(tmp_path, ana)
        app = _make_app(container)

        async with _client(app) as c:
            response = await c.get("/signup-static/js/main.js")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_signup_static_js_404_when_disabled(self):
        container = MagicMock()
        app = create_app(container, AsyncMock(spec=MatchNotifier))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/signup-static/js/main.js")

        assert response.status_code == 404
