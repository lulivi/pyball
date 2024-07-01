from typing import Callable

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ConversationHandler

from pyballbot.utils import bot_call_message_function


async def finish_conversation(reply_func: Callable, message: str) -> int:
    await bot_call_message_function(reply_func, message, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
