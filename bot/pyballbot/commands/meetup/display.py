from enum import Enum, auto

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.commands.utils import send_regulars_meetup_message
from pyballbot.logger import log_func
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.requests.types import Meetup
from pyballbot.settings import DISPLAY_DATETIME_FORMAT
from pyballbot.utils import bot_call_message_function


class DisplayMeetupState(Enum):
    DISPLAY_MEETUP = auto()


@log_func
async def ask_meetup_date_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> DisplayMeetupState:
    try:
        meetups = {
            meetup.date_time.strftime(DISPLAY_DATETIME_FORMAT): meetup
            for meetup in meetup_requests.get_all()
        }
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update.message.reply_text, f"There is a problem contacting Pyball core: {error}"
        )

    if not meetups:
        return await finish_conversation(
            update.message.reply_text, "There are no opened meetups. Please create one first."
        )

    context.chat_data["meetups"] = meetups

    await bot_call_message_function(
        update.message.reply_text,
        "Please, send the meetup date and time to display:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[meetup_date] for meetup_date in sorted(meetups.keys())],
            one_time_keyboard=True,
            input_field_placeholder="Meetup date and time",
        ),
    )
    return DisplayMeetupState.DISPLAY_MEETUP


@log_func
async def display_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    meetup: Meetup = context.chat_data["meetups"][update.message.text.strip()]

    await send_regulars_meetup_message(
        meetup_id=meetup.id,
        send_message_func=context.bot.send_message,
        delete_message_func=context.bot.delete_message,
        force=False,
    )

    return await finish_conversation()


@log_func
async def cancel_meetup_display(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Meetup display cancelled.")
