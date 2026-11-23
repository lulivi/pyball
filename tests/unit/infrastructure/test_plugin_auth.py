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

"""Tests for per-plugin credentials and their scopes."""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from pyball.infrastructure.http.auth import TokenAuthMiddleware
from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.settings import PluginConfig

_SIESTA = PluginConfig("siesta", ("./siesta",), frozenset({"meetups:read"}))


def _app(credentials: PluginCredentials) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TokenAuthMiddleware, manage_token="manage-tok")

    @app.get("/api/v1/thing", dependencies=[Depends(credentials.require("meetups:read"))])
    async def read_thing():
        return {"ok": True}

    @app.post("/api/v1/thing", dependencies=[Depends(credentials.require("meetups:write"))])
    async def write_thing():
        return {"ok": True}

    return app


async def _call(app, method, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.request(method, "/api/v1/thing", headers=headers)


def test_each_plugin_gets_its_own_token():
    """Two plugins never share a token, and a restart issues new ones."""
    other = PluginConfig("other", ("./other",), frozenset())
    creds = PluginCredentials([_SIESTA, other])
    assert creds.token_for("siesta") != creds.token_for("other")
    assert PluginCredentials([_SIESTA]).token_for("siesta") != creds.token_for("siesta")


@pytest.mark.asyncio
async def test_plugin_token_reaches_routes_within_its_scopes():
    """A plugin may read with meetups:read but not write."""
    creds = PluginCredentials([_SIESTA], manage_token="manage-tok")
    app = _app(creds)
    assert (await _call(app, "GET", creds.token_for("siesta"))).status_code == 200
    assert (await _call(app, "POST", creds.token_for("siesta"))).status_code == 403


@pytest.mark.asyncio
async def test_manage_token_has_every_scope():
    """The manage token works as a bearer on the plugin API."""
    app = _app(PluginCredentials([_SIESTA], manage_token="manage-tok"))
    assert (await _call(app, "POST", "manage-tok")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, "wrong"])
async def test_missing_or_unknown_token_is_401(token):
    """No bearer, or an unknown one, is refused."""
    app = _app(PluginCredentials([_SIESTA], manage_token="manage-tok"))
    assert (await _call(app, "GET", token)).status_code == 401


@pytest.mark.asyncio
async def test_plugin_token_is_refused_outside_the_plugin_api():
    """A plugin token is no key to /manage or the legacy API."""
    creds = PluginCredentials([_SIESTA], manage_token="manage-tok")
    app = _app(creds)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            "/api/meetup/active",
            headers={"Cookie": f"pyball_manage_token={creds.token_for('siesta')}"},
        )
        param = await c.get(f"/manage?token={creds.token_for('siesta')}")
    assert resp.status_code == 401
    assert param.status_code == 401
