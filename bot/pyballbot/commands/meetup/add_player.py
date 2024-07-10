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
    AddPlayerToMeetupError,
    CouldNotConnectToTheCore,
    MeetupIdDoesNotExist,
    PlayerIsAreadyCalled,
    PlayerNameDoesNotExist,
    PlayerQueryError,
)
from pyballbot.requests.types import Meetup, Player
from pyballbot.utils import bot_call_message_function


class AddPlayerToMeetupState(Enum):
    ASK_PLAYER_NAME = auto()
    ADD_PLAYER_TO_MEETUP = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_meetup_date_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> AddPlayerToMeetupState:
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
        await finish_conversation(
            update.message.reply_text, "There is no opened meetup. Please create one first."
        )
        return

    context.chat_data["meetups"] = meetups

    await bot_call_message_function(
        update.message.reply_text,
        "Please, send the meetup date and time to add the player to. Press /cancel to stop this"
        " conversation:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[meetup_date] for meetup_date in sorted(meetups.keys())],
            one_time_keyboard=True,
            input_field_placeholder="Meetup date and time",
        ),
    )

    return AddPlayerToMeetupState.ASK_PLAYER_NAME


async def save_meetup_date_time_ask_player_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> AddPlayerToMeetupState:
    selected_meetup: Meetup = context.chat_data["meetups"][update.message.text.strip()]
    context.chat_data["selected_meetup"] = selected_meetup

    all_players: List[Player] = player_requests.get_all()
    player_names_not_called_up = sorted(
        [player.name for player in all_players if player.id not in selected_meetup.players]
    )

    await bot_call_message_function(
        update.message.reply_text,
        "Please, select the player name to add to the meetup:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                player_tuple
                for player_tuple in zip(
                    player_names_not_called_up[::2], player_names_not_called_up[1::2]
                )
            ],
            one_time_keyboard=True,
            input_field_placeholder="Player selection",
        ),
    )
    return AddPlayerToMeetupState.ADD_PLAYER_TO_MEETUP


async def add_player_to_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    player_name: str = update.message.text.strip()
    meetup: Meetup = context.chat_data["selected_meetup"]
    try:
        meetup_requests.add_player_by_name(
            meetup_id=meetup.id,
            player_name=player_name,
        )
    except PlayerNameDoesNotExist as error:
        await bot_call_message_function(
            update.message.reply_text,
            f"Could not find any player with the name `{error.name}`. Please introduce correct"
            " player",
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME
    except PlayerQueryError as error:
        await bot_call_message_function(
            update.message.reply_text, f"Unexpected error getting the player: {error}"
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME
    except PlayerIsAreadyCalled as error:
        await bot_call_message_function(
            update.message.reply_text,
            f"The player is already called. Please enter another player name or /cancel the"
            f" conversation:",
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME
    except AddPlayerToMeetupError as error:
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
        update.message.reply_text, "The player was added to the meetup."
    )


@log_func
async def cancel_player_addition(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Adición del jugador cancelada.")
