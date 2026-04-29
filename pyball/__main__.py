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
"""Bot main file."""

import asyncio
import locale
import logging
import signal

import uvicorn

from pyball import __version__
from pyball.application.container import Container
from pyball.bot import create_application
from pyball.bot.handlers import (
    setup_general_handlers,
    setup_meetup_handlers,
    setup_player_handlers,
)
from pyball.infrastructure.http.app import create_app
from pyball.logger import config_logging
from pyball.settings import load_settings

logger = logging.getLogger(__name__)


class _Server(uvicorn.Server):
    """Uvicorn server that defers signal handling to the caller."""

    def install_signal_handlers(self) -> None:
        """No-op: signals are managed by main_async."""


def log_startup_info() -> None:
    """Log startup information."""
    logger.info("*" * 40)
    logger.info("PyBall v%s", __version__)
    logger.info("*" * 40)


async def main_async() -> None:
    """Start the bot and HTTP server under the same asyncio event loop."""
    config_logging()
    log_startup_info()

    settings = load_settings()
    container = Container()

    locale.setlocale(locale.LC_ALL, settings.pyball.locale)

    application = create_application()
    application.bot_data["container"] = container
    application.bot_data["settings"] = settings

    setup_player_handlers(application)
    setup_meetup_handlers(application)
    setup_general_handlers(application)

    fastapi_app = create_app(container, application.bot, settings)  # type: ignore[arg-type]
    server_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
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


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
