from pyballbot.utils import bot_call_message_function
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ConversationHandler


async def finish_conversation(update: Update, message: str) -> int:
    await bot_call_message_function(
        update.message.reply_text, message, reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
