from telegram import Update
from telegram.ext import ContextTypes

from pyballbot import __version__
from pyballbot.logger import log_func
from pyballbot.utils import bot_call_message_function, is_admin_chat


@log_func
async def command_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Message from wrong chat.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    help_text = (
        "Available commands:\n- /help: Show this help message.\n- /version: Show the bot version."
    )

    if is_admin_chat(update.message.chat_id):
        help_text = (
            f"{help_text}\n\nAdmin commands:\n- /player_create: Create a new player.\n-"
            " /player_rename: Rename a player.\n- /meetup_create: Create a new meetup.\n-"
            " /meetup_display: Show an already existent meetup.\n- /meetup_add_player: Add a"
            " player to an existing meetup.\n- /meetup_remove_player: Remove a player from an"
            " existing meetup.\n- /meetup_search_substitutes: Send a message to the substitutes"
            " channel to complete the meetup."
        )

    await bot_call_message_function(update.message.reply_text, help_text.replace("_", r"\_"))
