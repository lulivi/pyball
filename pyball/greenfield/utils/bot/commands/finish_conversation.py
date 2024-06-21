from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from pyball.greenfield.meetup.application.get_meetup import GetMeetup
from pyball.greenfield.meetup.infrastructure.bot_meetup import add_player_to_meetup_by_name
from pyball.greenfield.meetup.infrastructure.errors import (
    MeetupDateNotFound,
    PlayerIsAlreadyInMeetup,
    PlayerNameNotFound,
)
from pyball.greenfield.player.infrastructure.bot_player import create_player
from pyball.greenfield.player.infrastructure.errors import PlayerTelegramIdInUse
from pyball.greenfield.utils.bot.utils import bot_call_message_function
from pyball.logger import log_func


async def finish_conversation(update: Update, message: str) -> int:
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
