import logging

from enum import Enum, auto
from typing import List

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.logger import log_func
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import (
    CouldNotConnectToTheCore,
    PlayerIsNotCalled,
    PlayerNameDoesNotExist,
    PlayerQueryError,
    RemovePlayerFromMeetupError,
)
from pyballbot.requests.types import Meetup, Player
from pyballbot.utils import bot_call_message_function, get_two_column_string_list_keyboard


class RemovePlayerFromMeetupState(Enum):
    ASK_PLAYER_NAME = auto()
    REMOVE_PLAYER_FROM_MEETUP = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_meetup_date_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> RemovePlayerFromMeetupState:
    """Starts the conversation and asks the user about their gender."""
    try:
        meetups = {
            meetup.date_time.strftime("%A %d/%b/%Y %H:%M"): meetup
            for meetup in meetup_requests.get_all()
        }
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update.message.reply_text, f"There is a problem contacting Pyball core: {error}"
        )

    if not meetups:
        return await finish_conversation(
            update.message.reply_text, "There is no opened meetup. Please create one first."
        )

    context.chat_data["meetups"] = meetups

    await bot_call_message_function(
        update.message.reply_text,
        "Please, send the meetup date and time to remove the player from. Press /cancel to stop"
        " this conversation:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[meetup_date] for meetup_date in sorted(meetups.keys())],
            one_time_keyboard=True,
            input_field_placeholder="Meetup date and time",
        ),
    )

    return RemovePlayerFromMeetupState.ASK_PLAYER_NAME


async def save_meetup_date_time_ask_player_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> RemovePlayerFromMeetupState:
    selected_meetup: Meetup = context.chat_data["meetups"][update.message.text.strip()]
    context.chat_data["selected_meetup"] = selected_meetup

    all_players: List[Player] = player_requests.get_all()
    player_names_called_up = sorted(
        [player.name for player in all_players if player.id in selected_meetup.players]
    )

    if not player_names_called_up:
        return await finish_conversation(
            update.message.reply_text, "There are no players left in the meetup."
        )

    await bot_call_message_function(
        update.message.reply_text,
        "Please, select the player name to remove from the meetup:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=get_two_column_string_list_keyboard(player_names_called_up),
            one_time_keyboard=True,
            input_field_placeholder="Player selection",
        ),
    )
    return RemovePlayerFromMeetupState.REMOVE_PLAYER_FROM_MEETUP


async def remove_player_from_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player_name: str = update.message.text.strip()
    meetup: Meetup = context.chat_data["selected_meetup"]
    try:
        meetup_requests.remove_player_by_name(
            meetup_id=meetup.id,
            player_name=player_name,
        )
    except PlayerNameDoesNotExist as error:
        await bot_call_message_function(
            update.message.reply_text,
            f"Could not find any player with the name `{error.name}`. Please introduce correct"
            " player",
        )
        return RemovePlayerFromMeetupState.ASK_PLAYER_NAME
    except PlayerQueryError as error:
        await bot_call_message_function(
            update.message.reply_text, f"Unexpected error getting the player: {error}"
        )
        return RemovePlayerFromMeetupState.ASK_PLAYER_NAME
    except PlayerIsNotCalled as error:
        await bot_call_message_function(
            update.message.reply_text,
            f"The player is not int he meetup. Please enter another player name or /cancel the"
            f" conversation:",
        )
        return RemovePlayerFromMeetupState.ASK_PLAYER_NAME
    except RemovePlayerFromMeetupError as error:
        return await finish_conversation(
            update.message.reply_text,
            f"Unexpected error adding player `{player_name}` to meetup"
            f" `{context.chat_data['selected_meetup']}`",
        )
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update.message.reply_text, f"There is a problem contacting Pyball core: {error}"
        )

    return await finish_conversation(
        update.message.reply_text, "The player was removed from the meetup."
    )


@log_func
async def cancel_player_removal(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Player removal from meetup cancelled.")
