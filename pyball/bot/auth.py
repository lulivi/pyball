# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
