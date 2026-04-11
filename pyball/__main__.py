"""Bot main file."""

import asyncio
import logging

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    server = uvicorn.Server(server_config)

    async with application:
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot polling started")
        await server.serve()
        logger.info("HTTP server stopped — shutting down bot")
        await application.updater.stop()
        await application.stop()


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
