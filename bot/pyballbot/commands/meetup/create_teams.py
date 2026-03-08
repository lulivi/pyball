import datetime
import functools
import logging

from enum import Enum, auto
from typing import Callable, Dict, Tuple

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.commands.utils import get_meetup_date_time_from_message, update_meetup_messages
from pyballbot.logger import log_func
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests.errors import MeetupDateTimeDoesNotExist
from pyballbot.utils import bot_call_message_function


class CreateTeamsState(Enum):
    RECREATE_TEAMS = auto()


class CreateTeamsAction(Enum):
    RECREATE = "Recreate the teams"
    SAVE = "Save the teams and create the match"


@log_func
async def ask_what_to_do(update: Update, context: ContextTypes.DEFAULT_TYPE) -> CreateTeamsState:
    if not update.message or not update.message.reply_to_message:
        return await finish_conversation(
            update.message.reply_text, "This command must respond to an active meetup"
        )

    meetup_date = get_meetup_date_time_from_message(update.message.reply_to_message.text)

    try:
        meetup_id = meetup_requests.translate_date_to_id(date_time=meetup_date)
    except MeetupDateTimeDoesNotExist:
        return await finish_conversation(
            update.message.reply_text,
            f"Could not found the specified meetup `{meetup_date.isoformat()}`",
        )

    context.chat_data["selected_meetup_id"] = meetup_id

    return await recreate_or_save_teams(update=update, context=context)


@log_func
async def recreate_or_save_teams(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> CreateTeamsState:
    if update.message.text == CreateTeamsAction.SAVE.value:
        meetup_requests.create_matches(meetup_id=context.chat_data["selected_meetup_id"])
        return await finish_conversation(update.message.reply_text, "Match were created")

    meetup_requests.create_teams(meetup_id=context.chat_data["selected_meetup_id"])

    await update_meetup_messages(
        meetup_id=context.chat_data["selected_meetup_id"],
        send_message_func=context.bot.send_message,
        edit_message_func=context.bot.edit_message_text,
    )

    await bot_call_message_function(
        update.message.reply_text,
        "Please select whether to recreate the teams or to save them creating a match",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[action.value] for action in CreateTeamsAction],
            one_time_keyboard=True,
        ),
    )

    return CreateTeamsState.RECREATE_TEAMS


@log_func
async def cancel_match_creaation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Match creation cancelled.")
