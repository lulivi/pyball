"""Bot main file."""

import asyncio
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
    log_startup_info()

    settings = load_settings()
    container = Container()
    application = create_application()
    application.bot_data["container"] = container
    application.bot_data["settings"] = settings

    setup_player_handlers(application)
    setup_meetup_handlers(application)
    setup_general_handlers(application)

    fastapi_app = create_app(container, application.bot, settings)
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
