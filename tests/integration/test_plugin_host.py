"""Integration tests for hosting plugins: supervision, the siesta flow, and stream resume."""

# pylint: disable=redefined-outer-name

import asyncio
import socket
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
import uvicorn

from pyball.application.container import Container
from pyball.infrastructure.http.app import _Server, create_app, wait_until_serving
from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.infrastructure.plugins.event_log import EventLogNotifier
from pyball.infrastructure.plugins.supervisor import PluginSupervisor
from pyball.settings import AppSettings, Paths, PluginConfig, PyballConfig

_PLUGINS = Path(__file__).parent / "plugins"
_FAST = {"min_backoff": 0.05, "max_backoff": 0.2, "stable_after": 5.0, "stop_timeout": 1.0}


def _plugin(name: str, *args: str) -> PluginConfig:
    scopes = frozenset({"players:read", "meetups:read", "meetups:write"})
    return PluginConfig(name, (sys.executable, *args), scopes)


async def _until(condition, timeout: float = 10.0) -> None:
    async def poll():
        while not condition():
            await asyncio.sleep(0.05)

    await asyncio.wait_for(poll(), timeout)


@pytest.fixture
def container(tmp_path):
    """A real container over a temp data directory, with 12 regulars."""
    settings = AppSettings(
        pyball=PyballConfig(location="Campo", name="Test"),
        paths=Paths(_data_dir_override=str(tmp_path / "data")),
    )
    real = Container(settings)
    for i in range(12):
        real.create_player().execute(f"Regular_{i:02d}", "regular")
    return real


@pytest_asyncio.fixture
async def server(container):
    """Yield a function that serves the app for some plugins on an ephemeral port.

    It returns the plugin API URL and the plugins' credentials.
    """
    running: list[tuple[_Server, asyncio.Task]] = []

    async def serve(plugins: list[PluginConfig]) -> tuple[str, PluginCredentials]:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        credentials = PluginCredentials(plugins, manage_token="manage-tok")
        app = create_app(
            container, EventLogNotifier(container.event_log), plugin_credentials=credentials
        )
        uv = _Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", ws="none")
        )
        task = asyncio.create_task(uv.serve())
        await wait_until_serving(uv, task)
        running.append((uv, task))
        return f"http://127.0.0.1:{port}/api/v1", credentials

    yield serve
    container.event_log.close_subscribers()
    for uv, task in running:
        uv.should_exit = True
        await task


@pytest.mark.asyncio
async def test_crashing_plugin_is_restarted_and_the_core_keeps_serving(tmp_path, server):
    """A plugin that exits at once is started again, and the API still answers."""
    runs = tmp_path / "runs"
    crasher = _plugin(
        "crasher",
        "-c",
        f"open({str(runs)!r}, 'a').write('x'); raise SystemExit(1)",
    )
    api_url, credentials = await server([crasher])
    supervisor = PluginSupervisor([crasher], credentials, api_url, tmp_path, **_FAST)
    supervisor.start()
    try:
        await _until(lambda: runs.exists() and len(runs.read_text()) >= 3)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{api_url}/players", headers={"Authorization": "Bearer manage-tok"}
            )
        assert resp.status_code == 200
    finally:
        await supervisor.stop()


@pytest.mark.asyncio
async def test_stop_terminates_plugins_and_kills_the_stubborn(tmp_path, server):
    """Shutdown ends a plugin that ignores SIGTERM too, and starts nothing again."""
    started = tmp_path / "started"
    stubborn = _plugin(
        "stubborn",
        "-c",
        "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"open({str(started)!r}, 'a').write('x'); time.sleep(60)",
    )
    api_url, credentials = await server([stubborn])
    supervisor = PluginSupervisor([stubborn], credentials, api_url, tmp_path, **_FAST)
    supervisor.start()
    await _until(started.exists)

    await asyncio.wait_for(supervisor.stop(), 5)
    await asyncio.sleep(0.3)

    assert started.read_text() == "x"


@pytest.mark.asyncio
async def test_plugin_with_only_the_api_runs_the_siesta_draw(tmp_path, server, container):
    """12 signed up for 10: the plugin trims to capacity and makes teams on its own."""
    meetup = container.create_meetup().execute(datetime(2026, 11, 25, 20, 0))
    for player in container.player_repository.find_all():
        container.add_player_to_meetup_by_id().execute(meetup.date, player.id)
    done = tmp_path / "done"
    siesta = _plugin("siesta", str(_PLUGINS / "siesta_like.py"), str(done))
    api_url, credentials = await server([siesta])
    supervisor = PluginSupervisor([siesta], credentials, api_url, tmp_path, **_FAST)
    supervisor.start()
    try:
        await _until(done.exists)
    finally:
        await supervisor.stop()

    drawn = container.meetup_repository.find_by_datetime(meetup.date)
    assert len(drawn.players) == 10
    assert drawn.teams is not None


@pytest.mark.asyncio
async def test_plugin_opens_a_search_for_a_short_roster(tmp_path, server, container):
    """9 signed up for 10: the plugin opens a substitute search."""
    meetup = container.create_meetup().execute(datetime(2026, 11, 25, 20, 0))
    for player in container.player_repository.find_all()[:9]:
        container.add_player_to_meetup_by_id().execute(meetup.date, player.id)
    done = tmp_path / "done"
    siesta = _plugin("siesta", str(_PLUGINS / "siesta_like.py"), str(done))
    api_url, credentials = await server([siesta])
    supervisor = PluginSupervisor([siesta], credentials, api_url, tmp_path, **_FAST)
    supervisor.start()
    try:
        await _until(done.exists)
    finally:
        await supervisor.stop()

    assert container.meetup_repository.find_by_datetime(meetup.date).substitute_search


@pytest.mark.asyncio
async def test_reconnecting_client_gets_every_missed_event_once(server, container):
    """Read two events, drop the connection, miss two, reconnect: exactly the missing two."""
    api_url, _ = await server([])
    log = container.event_log
    meetup = container.create_meetup().execute(datetime(2026, 11, 25, 20, 0))
    for _ in range(2):
        log.append("meetup.updated", meetup)
    headers = {"Authorization": "Bearer manage-tok"}

    async def read_ids(count: int, extra_headers: dict) -> list[int]:
        ids: list[int] = []
        async with httpx.AsyncClient(timeout=5) as client:
            async with client.stream(
                "GET", f"{api_url}/events", headers={**headers, **extra_headers}
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("id: "):
                        ids.append(int(line[4:]))
                    if len(ids) == count:
                        return ids
        return ids

    first = await asyncio.wait_for(read_ids(2, {"Last-Event-ID": "0"}), 5)
    for _ in range(2):
        log.append("meetup.updated", meetup)  # happens while disconnected
    second = await asyncio.wait_for(read_ids(2, {"Last-Event-ID": str(first[-1])}), 5)

    assert first + second == [1, 2, 3, 4]
