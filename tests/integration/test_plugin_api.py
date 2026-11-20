"""Integration tests for the /api/v1 plugin API over JSON persistence."""

# pylint: disable=redefined-outer-name

import asyncio
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from pyball.application.container import Container
from pyball.infrastructure.http.app import create_app
from pyball.infrastructure.plugins.api import event_stream
from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.infrastructure.plugins.event_log import EventLogNotifier
from pyball.settings import AppSettings, Paths, PluginConfig, PyballConfig

DATE = "2026-11-25T20:00"
_SIESTA = PluginConfig(
    "siesta", ("./siesta",), frozenset({"players:read", "meetups:read", "meetups:write"})
)
_READER = PluginConfig("reader", ("./reader",), frozenset({"meetups:read"}))


@pytest.fixture
def container(tmp_path):
    """A real container over a temp data directory, with 12 regulars."""
    settings = AppSettings(
        pyball=PyballConfig(location="Campo", name="Test", manage_token="manage-tok"),
        paths=Paths(_data_dir_override=str(tmp_path)),
    )
    real = Container(settings)
    for i in range(12):
        real.create_player().execute(f"Regular_{i:02d}", "regular")
    return real


@pytest.fixture
def credentials():
    """Credentials for a siesta-like plugin and a read-only one."""
    return PluginCredentials([_SIESTA, _READER], manage_token="manage-tok")


@pytest_asyncio.fixture
async def siesta(container, credentials):
    """An HTTP client authenticated as the siesta plugin."""
    app = create_app(
        container,
        EventLogNotifier(container.event_log),
        manage_token="manage-tok",
        plugin_credentials=credentials,
    )
    headers = {"Authorization": f"Bearer {credentials.token_for('siesta')}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test/api/v1", headers=headers
    ) as client:
        yield client


async def _meetup_with(siesta, count: int) -> dict:
    meetup = (await siesta.post("/meetups", json={"date": DATE})).json()
    players = (await siesta.get("/players")).json()
    for player in players[:count]:
        meetup = (await siesta.put(f"/meetups/{meetup['id']}/players/{player['id']}")).json()
    return meetup


@pytest.mark.asyncio
async def test_siesta_draw_trims_to_capacity_and_builds_teams(siesta, container):
    """12 signed up for 10: one lineup call keeps 10 and builds two teams, as one event."""
    meetup = await _meetup_with(siesta, 12)
    before = container.event_log.last_id

    resp = await siesta.put(
        f"/meetups/{meetup['id']}/lineup",
        json={"players": meetup["players"][:10], "team_algorithm": "balanceado"},
    )

    body = resp.json()
    assert resp.status_code == 200
    assert len(body["players"]) == 10
    assert sorted(len(t["players"]) for t in body["teams"]) == [5, 5]
    assert [e["type"] for e in container.event_log.after(before)] == ["meetup.updated"]


@pytest.mark.asyncio
async def test_short_roster_opens_a_search_that_the_tenth_join_closes(siesta, container):
    """9 of 10: open a search; the 10th player closes it and the log says so."""
    meetup = await _meetup_with(siesta, 9)
    opened = await siesta.post(f"/meetups/{meetup['id']}/substitute-search")
    assert opened.json()["substitute_search"] is True

    tenth = (await siesta.get("/players")).json()[9]
    joined = (await siesta.put(f"/meetups/{meetup['id']}/players/{tenth['id']}")).json()

    assert joined["substitute_search"] is False
    types = [e["type"] for e in container.event_log.after(0)]
    assert types[-2:] == ["player.joined", "substitute_search.closed"]


@pytest.mark.asyncio
async def test_full_roster_cannot_search_until_capacity_rises(siesta):
    """10 of 10 refuses a search; raising the capacity to 12 allows it."""
    meetup = await _meetup_with(siesta, 10)
    assert (await siesta.post(f"/meetups/{meetup['id']}/substitute-search")).status_code == 409

    resized = await siesta.put(f"/meetups/{meetup['id']}/capacity", json={"capacity": 12})
    assert resized.json()["capacity"] == 12
    assert (await siesta.post(f"/meetups/{meetup['id']}/substitute-search")).status_code == 200


@pytest.mark.asyncio
async def test_create_meetup_with_its_own_capacity(siesta):
    """A plugin can create a 7 vs 8 meetup directly."""
    resp = await siesta.post("/meetups", json={"date": DATE, "capacity": 15})
    assert (resp.status_code, resp.json()["capacity"]) == (201, 15)


@pytest.mark.asyncio
async def test_unknown_player_in_lineup_is_422(siesta):
    """A lineup naming a player PyBall doesn't know is refused."""
    meetup = await _meetup_with(siesta, 2)
    resp = await siesta.put(
        f"/meetups/{meetup['id']}/lineup",
        json={"players": ["11111111-1111-4111-8111-111111111111"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_read_only_plugin_cannot_write(siesta, credentials):
    """A plugin without meetups:write gets 403 on a write."""
    meetup = await _meetup_with(siesta, 1)
    resp = await siesta.post(
        f"/meetups/{meetup['id']}/substitute-search",
        headers={"Authorization": f"Bearer {credentials.token_for('reader')}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_openapi_documents_only_the_plugin_api(siesta):
    """The v1 schema lists v1 routes and none of the /manage ones."""
    schema = (await siesta.get("/openapi.json")).json()
    assert "/meetups/{meetup_id}/lineup" in schema["paths"]
    assert not any(path.startswith("/api/meetup") for path in schema["paths"])


@pytest.mark.asyncio
async def test_stream_resumes_after_the_last_seen_event_in_order(container):
    """Reconnecting with the last id seen yields every later event once, then live ones."""
    log = container.event_log
    meetup = container.create_meetup().execute(datetime(2026, 11, 25, 20, 0))
    for _ in range(3):
        log.append("meetup.updated", meetup)

    stream = event_stream(log, after=1)
    frames = [await anext(stream) for _ in range(2)]
    log.append("meetup.updated", meetup)  # a live event after the replay
    frames.append(await anext(stream))
    log.close_subscribers()
    with pytest.raises(StopAsyncIteration):
        await anext(stream)

    assert [f.split("\n")[0] for f in frames] == ["id: 2", "id: 3", "id: 4"]


@pytest.mark.asyncio
async def test_stream_sends_keepalives_while_idle(container):
    """An idle stream sends a comment so proxies keep the connection open."""
    stream = event_stream(container.event_log, after=None, keepalive=0.01)
    assert await asyncio.wait_for(anext(stream), 1) == ": keepalive\n\n"
    await stream.aclose()
