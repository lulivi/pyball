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
"""The PyBall entrypoint: /manage, /match, optional /signup, the plugin API and plugins."""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

import uvicorn

from pyball.application.bootstrap import bootstrap_core
from pyball.infrastructure.alerts import config_alerts
from pyball.infrastructure.http.app import _Server, create_app, wait_until_serving
from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.infrastructure.plugins.event_log import EventLogNotifier
from pyball.infrastructure.plugins.supervisor import PluginSupervisor
from pyball.settings import SettingsValidationError


def main() -> None:
    """Start the server and its plugins."""
    parser = argparse.ArgumentParser(description="PyBall server (manage, match, optional signup)")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to config.toml (default: config.toml)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "Generate a deployment workspace"
            " (config.toml, compose.yaml, .env, README.md) and exit"
        ),
    )
    args = parser.parse_args()
    if args.bootstrap:
        from pyball.application.init_workspace import init_workspace  # pylint: disable=C0415

        init_workspace(args.config)
        return
    try:
        asyncio.run(_main_async(args.config))
    except SettingsValidationError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        sys.exit(1)


async def _main_async(config_path: Path) -> None:
    """Boot PyBall, with /signup enabled or not per config."""
    app_settings, container = bootstrap_core(config_path)
    config_alerts(app_settings.alerts)
    notifier = EventLogNotifier(container.event_log)
    credentials = PluginCredentials(app_settings.plugins, app_settings.pyball.manage_token)
    app = create_app(
        container,
        notifier,
        match_token=app_settings.pyball.match_token,
        manage_token=app_settings.pyball.manage_token,
        signup_token=app_settings.pyball.signup_token,
        enable_web_signup=app_settings.pyball.enable_web_signup,
        plugin_credentials=credentials,
    )
    supervisor = PluginSupervisor(
        app_settings.plugins,
        credentials,
        f"http://127.0.0.1:{app_settings.pyball.api_port}/api/v1",
        app_settings.paths.workspace,
    )

    server_config = uvicorn.Config(
        app, host="0.0.0.0", port=app_settings.pyball.api_port, log_level="info", log_config=None
    )
    server = _Server(server_config)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    server_task = asyncio.create_task(server.serve())
    await wait_until_serving(server, server_task)
    supervisor.start()
    await stop_event.wait()

    await supervisor.stop()
    container.event_log.close_subscribers()
    server.should_exit = True
    await server_task
