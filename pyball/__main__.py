"""Bot main file."""

import logging

from pyball import __version__
from pyball.application.container import Container
from pyball.bot import create_application
from pyball.bot.handlers import setup_meetup_handlers, setup_player_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_startup_info() -> None:
    """Log startup information."""
    logger.info("*" * 40)
    logger.info(f"PyBall v{__version__}")
    logger.info("*" * 40)


def main() -> None:
    """Start the bot."""
    log_startup_info()

    container = Container()
    application = create_application()
    application.bot_data["container"] = container

    setup_player_handlers(application)
    setup_meetup_handlers(application)

    application.run_polling()


if __name__ == "__main__":
    main()
