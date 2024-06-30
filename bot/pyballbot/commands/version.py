from telegram import Update
from telegram.ext import ContextTypes

from pyballbot import __version__
from pyballbot.logger import log_func
from pyballbot.utils import bot_call_message_function


@log_func
async def command_version(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show version of the application.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(update.message.reply_text, f"Pyball `{__version__}`")
