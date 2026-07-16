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


class TokenAuthMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-many-instance-attributes
    """Middleware that enforces static-token access control.

    Three tokens are supported, each scoped to its own subtree:
    - match_token: grants access to /match, GET /api/match/active, POST /api/match/finish
    - signup_token: grants access to /signup and /api/signup/*
    - manage_token: grants access to everything (superset of the other two)

    Token delivery:
    - ?token=<value> → validates, sets HttpOnly cookie, redirects to clean URL
    - Cookie pyball_<scope>_token=<value> → validates on every subsequent request

    When all three tokens are empty the middleware is disabled (no-op).
    """

    def __init__(
        self,
        app: "ASGIApp",
        match_token: str = "",
        manage_token: str = "",
        signup_token: str = "",
    ) -> None:
        """Initialise with the three static tokens."""
        super().__init__(app)
        self._match_token = match_token
        self._manage_token = manage_token
        self._signup_token = signup_token
        self._cookie_names = {
            "manage": "pyball_manage_token",
            "match": "pyball_match_token",
            "signup": "pyball_signup_token",
        }
        self._cookie_path = "/"
        self._public_paths = frozenset(
            [
                "/",
                "/favicon.ico",
                "/sw.js",
                "/manifest-match.json",
                "/manifest-manage.json",
            ]
        )
        self._manage_page = "/manage"
        self._match_page = "/match"
        self._match_api_routes = frozenset(
            [
                ("GET", "/api/match/active"),
                ("POST", "/api/match/finish"),
            ]
        )
        self._signup_page = "/signup"
        self._signup_api_prefix = "/api/signup/"
        self._api_prefix = "/api/"
        self._icons_prefix = "/icons/"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check token on every request."""
        if not self._match_token and not self._manage_token and not self._signup_token:
            return await call_next(request)

        path = request.url.path

        if self._is_public(path):
            return await call_next(request)

        token_param = request.query_params.get("token")
        if token_param is not None:
            return self._handle_token_param(request, token_param, path)

        manage_cookie = request.cookies.get(self._cookie_names["manage"])
        if manage_cookie and self._classify(manage_cookie) == "manage":
            return await call_next(request)

        required = self._required_scope(request.method, path)
        valid_scopes = set()
        for scope in ("match", "signup"):
            cookie = request.cookies.get(self._cookie_names[scope])
            if cookie and self._classify(cookie) == scope:
                valid_scopes.add(scope)

        if required in valid_scopes:
            return await call_next(request)
        if valid_scopes:
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return _unauthorized(path, self._api_prefix)

    def _handle_token_param(self, request: Request, token: str, path: str) -> Response:
        """Validate ?token=, set cookie, and redirect to the same path without the param."""
        token_type = self._classify(token)
        if token_type is None:
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
        required = self._required_scope(request.method, path)
        if token_type not in ("manage", required):
            return JSONResponse({"detail": "Forbidden"}, status_code=403)

        remaining = {k: v for k, v in request.query_params.items() if k != "token"}
        clean = path + ("?" + urllib.parse.urlencode(remaining) if remaining else "")
        response = RedirectResponse(url=clean, status_code=302)
        response.set_cookie(
            self._cookie_names[token_type],
            token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=31536000,
            path=self._cookie_path,
        )
        return response

    def _classify(self, token: str) -> str | None:
        """Return 'manage', 'match', 'signup', or None for an unrecognised token."""
        if self._manage_token and hmac.compare_digest(token, self._manage_token):
            return "manage"
        if self._match_token and hmac.compare_digest(token, self._match_token):
            return "match"
        if self._signup_token and hmac.compare_digest(token, self._signup_token):
            return "signup"
        return None

    def _is_public(self, path: str) -> bool:
        """Return True if the path requires no authentication."""
        return path in self._public_paths or path.startswith(self._icons_prefix)

    def _required_scope(self, method: str, path: str) -> str:
        """Return which token scope ('match', 'signup', or 'manage') a path requires."""
        if path == self._match_page or (method, path) in self._match_api_routes:
            return "match"
        if path == self._signup_page or path.startswith(self._signup_api_prefix):
            return "signup"
        return "manage"


# ── Private helpers ───────────────────────────────────────────────────────────


def _unauthorized(path: str, api_prefix: str = "/api/") -> Response:
    if path.startswith(api_prefix):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return HTMLResponse("<h1>Acceso no autorizado</h1>", status_code=401)
