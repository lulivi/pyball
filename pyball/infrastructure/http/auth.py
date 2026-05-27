"""Token-based authentication middleware for the FastAPI application."""
from __future__ import annotations

import hmac
import urllib.parse
from typing import TYPE_CHECKING, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp

_PUBLIC_PATHS = frozenset(
    ["/", "/favicon.ico", "/sw.js", "/qrcode.js", "/manifest-match.json", "/manifest-manage.json"]
)
_MATCH_API_ROUTES = frozenset([("GET", "/api/match/active"), ("POST", "/api/match/finish")])
_MANAGE_PAGE = "/manage"


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces static-token access control.

    Two tokens are supported:
    - match_token: grants access to /match, GET /api/match/active, POST /api/match/finish
    - manage_token: grants access to everything (superset of match_token)

    Token delivery:
    - ?token=<value> → validates, sets HttpOnly cookie, redirects to clean URL
    - Cookie pyball_token=<value> → validates on every subsequent request

    When both tokens are empty the middleware is disabled (no-op).
    """

    def __init__(self, app: "ASGIApp", match_token: str, manage_token: str) -> None:
        """Initialise with the two static tokens."""
        super().__init__(app)
        self._match_token = match_token
        self._manage_token = manage_token

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check token on every request."""
        if not self._match_token and not self._manage_token:
            return await call_next(request)

        path = request.url.path

        if _is_public(path):
            return await call_next(request)

        token_param = request.query_params.get("token")
        if token_param is not None:
            return self._handle_token_param(request, token_param, path)

        cookie_token = request.cookies.get("pyball_token")
        if not cookie_token:
            return _unauthorized(path)

        token_type = self._classify(cookie_token)
        if token_type is None:
            return _unauthorized(path)

        if _requires_manage(request.method, path) and token_type != "manage":
            return JSONResponse({"detail": "Forbidden"}, status_code=403)

        return await call_next(request)

    def _handle_token_param(self, request: Request, token: str, path: str) -> Response:
        """Validate ?token=, set cookie, and redirect to the same path without the param."""
        token_type = self._classify(token)
        if token_type is None:
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
        if _requires_manage(request.method, path) and token_type != "manage":
            return JSONResponse({"detail": "Forbidden"}, status_code=403)

        remaining = {k: v for k, v in request.query_params.items() if k != "token"}
        clean = path + ("?" + urllib.parse.urlencode(remaining) if remaining else "")
        response = RedirectResponse(url=clean, status_code=302)
        response.set_cookie(
            "pyball_token",
            token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=31536000,
            path="/",
        )
        return response

    def _classify(self, token: str) -> str | None:
        """Return 'manage', 'match', or None for an unrecognised token."""
        if self._manage_token and hmac.compare_digest(token, self._manage_token):
            return "manage"
        if self._match_token and hmac.compare_digest(token, self._match_token):
            return "match"
        return None


# ── Private helpers ───────────────────────────────────────────────────────────


def _is_public(path: str) -> bool:
    return path in _PUBLIC_PATHS or path.startswith("/icons/")


def _requires_manage(method: str, path: str) -> bool:
    if path == _MANAGE_PAGE:
        return True
    if (method, path) in _MATCH_API_ROUTES:
        return False
    return path.startswith("/api/")


def _unauthorized(path: str) -> Response:
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return HTMLResponse("<h1>Acceso no autorizado</h1>", status_code=401)
