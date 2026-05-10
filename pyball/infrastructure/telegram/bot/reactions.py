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
"""Reaction helper for bot command handlers."""
import logging

import telegram
from telegram import Bot, Message
from telegram.constants import ReactionEmoji

logger = logging.getLogger(__name__)


async def react_ok(bot: Bot, message: Message) -> None:
    """React ✅ to message; fall back to reply_text if reactions are unsupported."""
    try:
        await bot.set_message_reaction(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reaction=ReactionEmoji.OK_HAND_SIGN,
        )
    except telegram.error.TelegramError as error:
        logger.warning("Could not add reaction to %s: %s", message.message_id, str(error))
        await message.reply_text(ReactionEmoji.OK_HAND_SIGN)
