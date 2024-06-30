from telegram import Update
from telegram.ext import ContextTypes

from pyballbot import __version__
from pyballbot.logger import log_func
from pyballbot.utils import bot_call_message_function


@log_func
async def command_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Message from wrong chat.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(
        update.message.reply_text,
        "Comandos permitidos:\n\n- /help: Show this help message.\n- /version, /v: Show the"
        " bot version.\n- /player_create: Create a new player.\n- /meetup_create: Create a new"
        " meetup.\n- /meetup_add_player: Add a player to an existing meetup.",
    )
