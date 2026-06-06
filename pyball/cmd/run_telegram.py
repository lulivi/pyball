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
"""Telegram+FastAPI topology entrypoint."""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

import uvicorn

from pyball.application.bootstrap import bootstrap_core
from pyball.infrastructure.http.app import _Server, create_app
from pyball.infrastructure.telegram.bot.entrypoint import create_application
from pyball.infrastructure.telegram.bot.handlers import (
    setup_general_handlers,
    setup_meetup_handlers,
    setup_player_handlers,
)
from pyball.infrastructure.telegram.logging import config_telegram_logging
from pyball.infrastructure.telegram.notifications import TelegramMatchNotifier
from pyball.infrastructure.telegram.settings import load_telegram_app_settings
from pyball.settings import SettingsValidationError

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the Telegram bot and FastAPI server together."""
    parser = argparse.ArgumentParser(description="PyBall Telegram+web server")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to config.toml (default: config.toml)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(_main_async(args.config))
    except SettingsValidationError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        sys.exit(1)


async def _main_async(config_path: Path) -> None:
    """Boot the Telegram+FastAPI topology."""
    app_settings, container = bootstrap_core(config_path)
    tg_settings = load_telegram_app_settings(app_settings, config_path)
    config_telegram_logging(tg_settings.telegram)

    application = create_application(tg_settings)
    application.bot_data["container"] = container
    application.bot_data["settings"] = tg_settings

    setup_player_handlers(application)
    setup_meetup_handlers(application)
    setup_general_handlers(application)

    notifier = TelegramMatchNotifier(application.bot, tg_settings, container)
    fastapi_app = create_app(
        container,
        notifier,
        match_token=app_settings.pyball.match_token,
        manage_token=app_settings.pyball.manage_token,
        path_prefix=app_settings.pyball.name.lower().replace(" ", "-"),
    )
    server_config = uvicorn.Config(
        fastapi_app, host="0.0.0.0", port=app_settings.pyball.api_port, log_level="info"
    )
    server = _Server(server_config)

    assert application.updater is not None, "Updater must be set before starting"

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        if not stop_event.is_set():
            logger.info("Shutdown signal received")
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    async with application:
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot polling started")

        server_task = asyncio.create_task(server.serve())

        await stop_event.wait()

        logger.info("Stopping bot polling...")
        await application.updater.stop()
        await application.stop()

        logger.info("Stopping HTTP server...")
        server.should_exit = True
        await server_task

        logger.info("All services stopped")
