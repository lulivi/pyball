from typing import Callable, Optional

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ConversationHandler

from pyballbot.utils import bot_call_message_function


async def finish_conversation(reply_func: Optional[Callable] = None, message: str = "") -> int:
    if reply_func and message:
        await bot_call_message_function(reply_func, message, reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END
