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
"""FastAPI application factory."""
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pyball.infrastructure.http.auth import TokenAuthMiddleware
from pyball.infrastructure.http.routes import (
    register_match_routes,
    register_meetup_routes,
    register_player_routes,
    register_static_routes,
)
from pyball.infrastructure.plugins.api import create_plugin_api
from pyball.infrastructure.plugins.auth import PluginCredentials

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier

_DEFAULT_STATIC_DIR = Path(__file__).parent / "static"


def create_app(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    container: "Container",
    notifier: "MatchNotifier",
    static_dir: Path = _DEFAULT_STATIC_DIR,
    match_token: str = "",
    manage_token: str = "",
    plugin_credentials: PluginCredentials | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application, with the plugin API at /api/v1."""
    app = FastAPI(title="PyBall API")

    if match_token or manage_token:
        app.add_middleware(
            TokenAuthMiddleware,
            match_token=match_token,
            manage_token=manage_token,
        )

    register_static_routes(app, static_dir, container)
    register_match_routes(app, container, notifier)
    register_player_routes(app, container)
    register_meetup_routes(app, container, notifier)

    credentials = plugin_credentials or PluginCredentials([], manage_token)
    app.mount("/api/v1", create_plugin_api(container, notifier, credentials))

    icons_dir = Path(container.icons_dir) if container.icons_dir else None
    if icons_dir and icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


async def wait_until_serving(server: uvicorn.Server, server_task: asyncio.Task) -> None:
    """Return once ``server`` accepts connections, or as soon as it fails to start."""
    while not server.started and not server_task.done():
        await asyncio.sleep(0.05)


class _Server(uvicorn.Server):
    """Uvicorn server that defers signal handling to the caller."""

    def install_signal_handlers(self) -> None:
        """No-op: signals are managed by the entrypoint."""
