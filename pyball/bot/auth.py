"""Authorization utilities for bot handlers."""

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def authorized(func: Callable) -> Callable:
    """Restrict handler to authorized users only.

    Checks if the user's Telegram ID is in ADMINS_IDS.
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user:
            logger.warning("No effective user in update")
            return

        settings = context.bot_data.get("settings")
        if not settings:
            logger.error("Settings not found in bot_data")
            return

        user_id = update.effective_user.id

        if not settings.telegram.is_authorized(user_id):
            logger.warning("Unauthorized access attempt from user ID: %s", user_id)
            message = update.message
            if message is not None:
                await message.reply_text(
                    "Unauthorized. You don't have permission to run this command."
                )
            return

        return await func(update, context)

    return wrapper
