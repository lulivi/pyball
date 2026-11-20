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
"""Per-plugin credentials and the scope check every /api/v1 route runs."""

from __future__ import annotations

import hmac
import secrets
from typing import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pyball.settings import PLUGIN_SCOPES, PluginConfig


class PluginCredentials:
    """One random bearer token per declared plugin, generated at each start, never stored.

    The manage token, when set, is accepted too and grants every scope.
    """

    def __init__(self, plugins: list[PluginConfig], manage_token: str = "") -> None:
        """Generate a token for each plugin."""
        self._tokens = {p.name: secrets.token_urlsafe(32) for p in plugins}
        self._scopes = {self._tokens[p.name]: p.scopes for p in plugins}
        self._manage_token = manage_token

    def token_for(self, plugin_name: str) -> str:
        """Return the token handed to ``plugin_name`` as PYBALL_API_TOKEN."""
        return self._tokens[plugin_name]

    def scopes_for(self, token: str) -> frozenset[str] | None:
        """Return the scopes ``token`` grants, or None if it is no valid token."""
        if self._manage_token and hmac.compare_digest(token, self._manage_token):
            return frozenset(PLUGIN_SCOPES)
        for known, scopes in self._scopes.items():
            if hmac.compare_digest(token, known):
                return scopes
        return None

    def require(self, scope: str) -> Callable[..., None]:
        """Return a FastAPI dependency that lets through only bearers holding ``scope``.

        It declares bearer authentication in the OpenAPI schema, so /api/v1/docs offers it.
        """

        def check(bearer: HTTPAuthorizationCredentials | None = Depends(_BEARER)) -> None:
            scopes = self.scopes_for(bearer.credentials) if bearer else None
            if scopes is None:
                raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
            if scope not in scopes:
                raise HTTPException(403, f"Missing scope {scope}")

        return check


_BEARER = HTTPBearer(auto_error=False, description="PYBALL_API_TOKEN, or the manage token")
