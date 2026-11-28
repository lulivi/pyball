# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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

    Two tokens are supported:
    - match_token: grants access to /match, GET /api/match/active, POST /api/match/finish
    - manage_token: grants access to everything (superset of match_token)

    Static assets (/js/*, /icons/*) carry no player data and are
    always public, same as the pages' own JS was already documented to be — only the
    page shells and the API are gated.

    Token delivery:
    - ?token=<value> → validates, sets HttpOnly cookie, redirects to clean URL
    - Cookie pyball_<scope>_token=<value> → validates on every subsequent request

    When both tokens are empty the middleware is disabled (no-op).

    The plugin API (/api/v1/*) is left alone: its routes check bearer tokens themselves.
    """

    def __init__(
        self,
        app: "ASGIApp",
        match_token: str = "",
        manage_token: str = "",
    ) -> None:
        """Initialise with the two static tokens."""
        super().__init__(app)
        self._match_token = match_token
        self._manage_token = manage_token
        self._cookie_names = {
            "manage": "pyball_manage_token",
            "match": "pyball_match_token",
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
        self._match_page = "/match"
        self._match_api_routes = frozenset(
            [
                ("GET", "/api/match/active"),
                ("POST", "/api/match/finish"),
            ]
        )
        self._api_prefix = "/api/"
        self._plugin_api_prefix = "/api/v1/"
        self._icons_prefix = "/icons/"
        self._js_prefix = "/js/"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check token on every request."""
        if not self._match_token and not self._manage_token:
            return await call_next(request)

        path = request.url.path

        if self._is_public(path) or path.startswith(self._plugin_api_prefix):
            return await call_next(request)

        token_param = request.query_params.get("token")
        if token_param is not None:
            return self._handle_token_param(request, token_param, path)

        manage_cookie = request.cookies.get(self._cookie_names["manage"])
        if manage_cookie and self._classify(manage_cookie) == "manage":
            return await call_next(request)

        required = self._required_scope(request.method, path)
        match_cookie = request.cookies.get(self._cookie_names["match"])
        if match_cookie and self._classify(match_cookie) == "match":
            if required == "match":
                return await call_next(request)
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
        """Return 'manage', 'match', or None for an unrecognised token."""
        if self._manage_token and hmac.compare_digest(token, self._manage_token):
            return "manage"
        if self._match_token and hmac.compare_digest(token, self._match_token):
            return "match"
        return None

    def _is_public(self, path: str) -> bool:
        """Return True if the path requires no authentication.

        Static assets (JS, icons) carry no player data and are the same for every
        visitor, so — like the page shells they support (/match, /manage) —
        only the *pages* and the API are gated, never the scripts that render them.
        """
        public_prefixes = (self._icons_prefix, self._js_prefix)
        return path in self._public_paths or path.startswith(public_prefixes)

    def _required_scope(self, method: str, path: str) -> str:
        """Return which token scope ('match' or 'manage') a path requires."""
        if path == self._match_page or (method, path) in self._match_api_routes:
            return "match"
        return "manage"


# ── Private helpers ───────────────────────────────────────────────────────────


def _unauthorized(path: str, api_prefix: str = "/api/") -> Response:
    if path.startswith(api_prefix):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return HTMLResponse("<h1>Acceso no autorizado</h1>", status_code=401)
