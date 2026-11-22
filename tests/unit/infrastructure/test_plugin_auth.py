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
