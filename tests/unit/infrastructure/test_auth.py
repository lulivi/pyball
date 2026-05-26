"""Unit tests for TokenAuthMiddleware."""
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from pyball.infrastructure.http.auth import TokenAuthMiddleware

MATCH_TOKEN = "match-tok"
MANAGE_TOKEN = "manage-tok"


def _make_app(match_token: str = MATCH_TOKEN, manage_token: str = MANAGE_TOKEN):
    """Minimal Starlette app with the middleware and representative routes."""

    async def root(request: Request):
        return JSONResponse({"page": "root"})

    async def match_page(request: Request):
        return JSONResponse({"page": "match"})

    async def manage_page(request: Request):
        return JSONResponse({"page": "manage"})

    async def api_match_active(request: Request):
        return JSONResponse({"active": True})

    async def api_match_finish(request: Request):
        return JSONResponse({"done": True})

    async def api_admin(request: Request):
        return JSONResponse({"admin": True})

    routes = [
        Route("/", root),
        Route("/match", match_page),
        Route("/manage", manage_page),
        Route("/api/match/active", api_match_active),
        Route("/api/match/finish", api_match_finish, methods=["POST"]),
        Route("/api/admin", api_admin),
    ]
    app = Starlette(routes=routes)
    app.add_middleware(TokenAuthMiddleware, match_token=match_token, manage_token=manage_token)
    return app


class TestPublicPaths:
    """Public paths are accessible without any token."""

    @pytest.mark.asyncio
    async def test_root_is_public(self):
        """GET / returns 200 with no token."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_icons_prefix_is_public(self):
        """/icons/* paths pass through the middleware (router may 404 — not 401)."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/icons/icon-192.png")
        assert response.status_code != 401


class TestUnauthenticatedRequests:
    """Requests without a valid token or cookie are rejected."""

    @pytest.mark.asyncio
    async def test_match_page_returns_401_html(self):
        """GET /match returns 401 HTML when unauthenticated."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/match")
        assert response.status_code == 401
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_api_route_returns_401_json(self):
        """GET /api/* returns 401 JSON when unauthenticated."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/api/match/active")
        assert response.status_code == 401
        assert response.json() == {"detail": "Unauthorized"}

    @pytest.mark.asyncio
    async def test_manage_page_returns_401_html(self):
        """GET /manage returns 401 HTML when unauthenticated."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/manage")
        assert response.status_code == 401


class TestMatchTokenCookieAccess:
    """match_token cookie grants access to match routes only."""

    @pytest.mark.asyncio
    async def test_allows_match_page(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MATCH_TOKEN)
            response = await c.get("/match")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_api_match_active(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MATCH_TOKEN)
            response = await c.get("/api/match/active")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_api_match_finish(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MATCH_TOKEN)
            response = await c.post("/api/match/finish")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_denies_manage_page(self):
        """match_token must not access /manage."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MATCH_TOKEN)
            response = await c.get("/manage")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_denies_other_api_routes(self):
        """match_token must not access admin API routes."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MATCH_TOKEN)
            response = await c.get("/api/admin")
        assert response.status_code == 403


class TestManageTokenCookieAccess:
    """manage_token cookie grants access to all routes."""

    @pytest.mark.asyncio
    async def test_allows_manage_page(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MANAGE_TOKEN)
            response = await c.get("/manage")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_match_page(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MANAGE_TOKEN)
            response = await c.get("/match")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_other_api_routes(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", MANAGE_TOKEN)
            response = await c.get("/api/admin")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_cookie_returns_401(self):
        """A cookie with an unrecognised token value is rejected."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c.cookies.set("pyball_token", "wrong-token")
            response = await c.get("/match")
        assert response.status_code == 401


class TestTokenQueryParam:
    """?token= param sets a cookie and redirects to the clean URL."""

    @pytest.mark.asyncio
    async def test_valid_match_token_sets_cookie_and_redirects(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c:
            response = await c.get(f"/match?token={MATCH_TOKEN}")
        assert response.status_code == 302
        assert response.headers["location"] == "/match"
        set_cookie = response.headers.get("set-cookie", "")
        assert "pyball_token" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=lax" in set_cookie
        assert "Max-Age=31536000" in set_cookie

    @pytest.mark.asyncio
    async def test_valid_manage_token_sets_cookie_and_redirects(self):
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c:
            response = await c.get(f"/manage?token={MANAGE_TOKEN}")
        assert response.status_code == 302
        assert response.headers["location"] == "/manage"

    @pytest.mark.asyncio
    async def test_match_token_on_manage_path_returns_403(self):
        """match_token cannot be used to set a cookie for /manage."""
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get(f"/manage?token={MATCH_TOKEN}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        app = _make_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            response = await c.get("/match?token=wrong")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_other_query_params_preserved_in_redirect(self):
        """Non-token query params survive the redirect."""
        app = _make_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c:
            response = await c.get(f"/match?token={MATCH_TOKEN}&date=2026-05-26T20%3A00")
        assert response.status_code == 302
        location = response.headers["location"]
        assert "token" not in location
        assert "date=" in location


class TestMiddlewareDisabled:
    """When both tokens are empty the middleware is a no-op."""

    @pytest.mark.asyncio
    async def test_all_routes_accessible_without_tokens(self):
        app = _make_app(match_token="", manage_token="")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r1 = await c.get("/match")
            r2 = await c.get("/manage")
            r3 = await c.get("/api/admin")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
