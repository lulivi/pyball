import datetime
import functools
import logging

from enum import Enum, auto
from typing import Tuple

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.logger import log_func
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests.errors import (
    CouldNotConnectToTheCore,
    MeetupCreationError,
    MeetupDateTimeIsAlreadyInUse,
)
from pyballbot.settings import DATETIME_FORMAT
from pyballbot.utils import bot_call_message_function


class CreateMeetupState(Enum):
    SELECT_LOCATION = auto()
    SELECT_TEAM_SIZES = auto()
    SAVE_MEETUP = auto()


class NewMeetupDateTime(Enum):
    NEXT_WEDNESDAY = "El siguiente miércoles a las 20h"


class NewMeetupLocation(Enum):
    CARTUJA_F5 = "Campo de futbol sala de cesped de Cartuja"
    FUENTENUEVA_PAVELLON = "Pabellón 1 de futbol sala de Fuentenueva"
    FUENTENUEVA_F5 = "Campo de futbol sala de pavimento de Fuentenueva"
    CARTUJA_F7 = "Campo de futbol 7 de Cartuja"
    FUENTENUEVA_F7 = "Campo de futbol 7 de Fuentenueva"


class NewMeetupTeamSizes(Enum):
    FIVE_SIX = "5, 6"
    SEVEN_EIGHT = "7, 8"


logger = logging.getLogger(__name__)


@log_func
async def ask_date_time(update: Update, _: ContextTypes.DEFAULT_TYPE) -> CreateMeetupState:
    """Starts the conversation and asks the user about their gender."""
    await bot_call_message_function(
        update.message.reply_text,
        "Por favor, selecciona la fecha y hora de la convocatoria o introdúcela a mano en el"
        " formato `DD/mmm/YYYY HH:MM` (Ej.:"
        f" `{datetime.datetime.fromtimestamp(1234).strftime(DATETIME_FORMAT)}`).",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[NewMeetupDateTime.NEXT_WEDNESDAY.value]],
            one_time_keyboard=True,
            input_field_placeholder="Fecha y hora de la convocatoria",
        ),
    )

    return CreateMeetupState.SELECT_LOCATION


@log_func
async def save_date_time_ask_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> CreateMeetupState:
    date_parser = {
        NewMeetupDateTime.NEXT_WEDNESDAY.value: get_next_wednesday,
    }
    context.chat_data["date_time"] = date_parser.get(
        update.message.text, functools.partial(parse_date_time, update.message.text)
    )()

    await bot_call_message_function(
        update.message.reply_text,
        "Por favor, selecciona o introduce la localización de la convocatoria",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[location.value] for location in NewMeetupLocation],
            one_time_keyboard=True,
            input_field_placeholder="Localización de la convocatoria",
        ),
    )
    return CreateMeetupState.SELECT_TEAM_SIZES


def get_next_wednesday() -> datetime.datetime:
    current_date = datetime.date.today()
    next_wednesday = current_date + datetime.timedelta(days=((2 - current_date.weekday()) % 7))
    return datetime.datetime(
        year=next_wednesday.year, month=next_wednesday.month, day=next_wednesday.day, hour=20
    )


def parse_date_time(date: str) -> datetime.date:
    return datetime.datetime.strptime(date, DATETIME_FORMAT)


@log_func
async def save_location_ask_team_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data["location"] = update.message.text.strip()

    await bot_call_message_function(
        update.message.reply_text,
        f"Cuáles son los posibles tamaños de equipos? Indique en una lista de números se"
        f" parados por coma `<número> [, <número> [...]]` Ej: `5, 6`.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[team_sizes.value] for team_sizes in NewMeetupTeamSizes],
            one_time_keyboard=True,
            input_field_placeholder="Tamaños de equipo",
        ),
    )

    return CreateMeetupState.SAVE_MEETUP


@log_func
async def save_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        team_sizes = parse_team_sizes(update.message.text)
    except ValueError:
        await bot_call_message_function(
            update.message.reply_text,
            "Please enter a valid value of the possible team sizes:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[team_sizes.value] for team_sizes in NewMeetupTeamSizes],
                one_time_keyboard=True,
                input_field_placeholder="Tamaños de equipo",
            ),
        )
        return CreateMeetupState.SAVE_MEETUP

    try:
        meetup_requests.create(
            date_time=context.chat_data["date_time"],
            location=context.chat_data["location"],
            possible_team_sizes=team_sizes,
        )
    except MeetupDateTimeIsAlreadyInUse as error:
        return await finish_conversation(
            update,
            "The meetup date and time is already in use. Please, restart the meetup creation.",
        )
    except MeetupCreationError as error:
        return await finish_conversation(
            update,
            f"Unknown error ocurred creating the meetup: {str(error)}",
        )
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update, f"There is a problem contacting Pyball core: {error}"
        )

    return await finish_conversation(
        update,
        "The meetup was created successfully with date and time:"
        f" {context.chat_data['date_time']}",
    )


def parse_team_sizes(string_team_sizes: str) -> Tuple[str, ...]:
    return tuple(int(size.strip()) for size in string_team_sizes.split(","))


@log_func
async def cancel_meetup_creation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update, "The meetup creation was cancelled.")
