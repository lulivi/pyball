import logging

from enum import Enum, auto

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pyball.greenfield.meetup.application.get_meetup import GetMeetup
from pyball.greenfield.meetup.infrastructure.bot_meetup import add_player_to_meetup_by_name
from pyball.greenfield.meetup.infrastructure.errors import (
    MeetupDateNotFound,
    PlayerIsAlreadyInMeetup,
    PlayerNameNotFound,
)
from pyball.greenfield.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository
from pyball.greenfield.utils.bot.commands.finish_conversation import finish_conversation
from pyball.greenfield.utils.bot.utils import bot_call_message_function
from pyball.logger import log_func


class AddPlayerToMeetupState(Enum):
    ASK_PLAYER_NAME = auto()
    ADD_PLAYER_TO_MEETUP = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_meetup_date_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> AddPlayerToMeetupState:
    """Starts the conversation and asks the user about their gender."""
    meetup_dates = {
        meetup.date_time.strftime("%A %d/%b/%Y %H:%M"): meetup.date_time
        for meetup in GetMeetup(MeetupJsonRepository()).all()
    }

    context.chat_data["meetups"] = meetup_dates

    await bot_call_message_function(
        update.message.reply_text,
        (
            "Por favor, introduce la fecha de la convocatoria a la que añadir el jugador. Pulsa"
            " /cancel para cancelar el añadido"
        ),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[meetup_date] for meetup_date in sorted(meetup_dates.keys())],
            one_time_keyboard=True,
            input_field_placeholder="Fecha y hora de la convocatoria",
        ),
    )

    return AddPlayerToMeetupState.ASK_PLAYER_NAME


async def save_meetup_date_time_ask_player_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> AddPlayerToMeetupState:
    context.chat_data["selected_meetup"] = context.chat_data["meetups"][
        update.message.text.strip()
    ]

    await bot_call_message_function(
        update.message.reply_text,
        "Por favor, introduce el nombre del jugador que será añadido a la convocatoria.",
    )
    return AddPlayerToMeetupState.ADD_PLAYER_TO_MEETUP


async def add_player_to_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        add_player_to_meetup_by_name(
            meetup_date_time=context.chat_data["selected_meetup"],
            player_name=update.message.text.strip(),
        )
    except PlayerIsAlreadyInMeetup:
        await bot_call_message_function(
            update.message.reply_text,
            (
                "The player was already in the meetup. Please introduce another player or /cancel"
                " the command."
            ),
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME
    except PlayerNameNotFound:
        await bot_call_message_function(
            update.message.reply_text,
            "Could not find any player with that name. Please introduce correct player",
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME
    except MeetupDateNotFound:
        await bot_call_message_function(
            update.message.reply_text,
            "Could not find any meetup with that date. Introduce a proper date.",
        )
        return AddPlayerToMeetupState.ASK_PLAYER_NAME

    return await finish_conversation(update, "Se ha añadido el jugador a la convocatoria.")


@log_func
async def cancel_player_addition(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update, "Adición del jugador cancelada.")
