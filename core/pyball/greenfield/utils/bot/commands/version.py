from telegram import Update
from telegram.ext import ContextTypes

from pyball import __version__
from pyball.greenfield.utils.bot.utils import bot_call_message_function
from pyball.logger import log_func


@log_func
async def command_version(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show version of the application.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(update.message.reply_text, f"Pyball `{__version__}`")
