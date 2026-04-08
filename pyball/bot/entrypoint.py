"""Bot application entrypoint."""

from telegram.ext import Application, CallbackQueryHandler

from pyball.bot.callbacks import callback_handler
from pyball.settings import load_settings


def create_application() -> Application:
    """Create and configure the Telegram application."""
    settings = load_settings()
    application = Application.builder().token(settings.telegram.bot_token).build()
    application.bot_data["settings"] = settings
    application.add_handler(CallbackQueryHandler(callback_handler))
    return application
