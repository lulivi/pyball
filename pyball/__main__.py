"""Bot main file."""

import logging

from pyball import __version__
from pyball.bot import create_application
from pyball.bot.handlers import setup_player_handlers, setup_meetup_handlers
from pyball.application.container import Container

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
    application = create_application()
    container = Container()
    setup_player_handlers(application)
    setup_meetup_handlers(application, container)
    application.run_polling()


if __name__ == "__main__":
    main()
