import functools
import logging

from enum import Enum
from typing import Callable, List

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from pyballbot.logger import log_func
from pyballbot.settings import ADMINS_IDS

logger = logging.getLogger(__name__)


def enum_as_regex(enum: Enum) -> str:
    inner_part = ")|(".join([location.value for location in enum])
    return f"({inner_part})"


def get_two_column_string_list_keyboard(string_list: List[str]) -> List[str]:
    pair_list = [player_tuple for player_tuple in zip(string_list[::2], string_list[1::2])]

    if len(string_list) % 2 != 0:
        pair_list.append((string_list.pop(),))

    return pair_list


def command_ensure_admin(func):
    """Ensure the command is being executed by an admin."""

    @functools.wraps(func)
    async def wrapper_only_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the user executing the command is admin."""
        if update.message is None or update.message.from_user is None:
            return

        user_id = update.message.from_user.id

        if ADMINS_IDS and user_id not in ADMINS_IDS:
            logger.debug(f"User {user_id} is not an admin ({ADMINS_IDS})")
            await update.message.reply_text("No tienes permisos para ejecutar este comando.")
            return

        logger.debug(f"User {user_id} is an admin ({ADMINS_IDS})")

        return await func(update, context)

    return wrapper_only_admin


def is_admin_chat(chat_id: int) -> bool:
    if ADMINS_IDS:
        return chat_id in ADMINS_IDS

    return False


@log_func
async def bot_call_message_function(
    message_function: Callable,
    text: str,
    *args,
    **kwargs,
) -> Message:
    """Call bot function with desired args.

    :param message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    return await message_function(
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        *args,
        **kwargs,
    )
