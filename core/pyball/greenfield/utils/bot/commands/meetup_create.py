#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import datetime
import functools
import logging

from enum import Enum, auto
from typing import Tuple

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyball.greenfield.meetup.infrastructure.bot_meetup import create_meetup
from pyball.greenfield.meetup.infrastructure.errors import MeetupDateAlreadyUsed
from pyball.greenfield.utils.bot.commands.finish_conversation import finish_conversation
from pyball.logger import log_func


class CreateMeetupState(Enum):
    SELECT_LOCATION = auto()
    SELECT_TEAM_SIZES = auto()
    SAVE_MEETUP = auto()


class NewMeetupDateTime(Enum):
    NEXT_WEDNESDAY = "El siguiente miércoles a las 20h"


class NewMeetupLocation(Enum):
    CARTUJA_F5 = "Campo de futbol sala de cesped de Cartuja"
    CARTUJA_F7 = "Campo de futbol 7 de Cartuja"
    FUENTENUEVA_F5 = "Campo de futbol sala de pavimento de Fuentenueva"
    FUENTENUEVA_PAVELLON = "Pabellón de futbol sala de Fuentenueva"
    FUENTENUEVA_F7 = "Campo de futbol 7 de Fuentenueva"


class NewMeetupTeamSizes(Enum):
    FIVE_SIX = "5, 6"
    SEVEN_EIGHT = "7, 8"


logger = logging.getLogger(__name__)


@log_func
async def ask_date_time(update: Update, _: ContextTypes.DEFAULT_TYPE) -> CreateMeetupState:
    """Starts the conversation and asks the user about their gender."""
    await update.message.reply_text(
        (
            "Por favor, selecciona la fecha y hora de la convocatoria o introdúcela a mano en el"
            " formato `DD/mmm/YYYY HH:MM` (Ej. `20/Jun/2024 21:30`)."
        ),
        parse_mode=ParseMode.MARKDOWN,
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

    await update.message.reply_text(
        "Por favor, selecciona o introduce la localización de la convocatoria",
        parse_mode=ParseMode.MARKDOWN,
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
    return datetime.datetime.strptime(date, "%d/%b/%Y %H:%M")


@log_func
async def save_location_ask_team_sizes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data["location"] = update.message.text.strip()

    await update.message.reply_text(
        (
            f"Cuáles son los posibles tamaños de equipos? Indique en una lista de números se"
            f" parados por coma `<número> [, <número> [...]]` Ej: `5, 6`."
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[team_sizes.value] for team_sizes in NewMeetupTeamSizes],
            one_time_keyboard=True,
            input_field_placeholder="Tamaños de equipo",
        ),
    )

    return CreateMeetupState.SAVE_MEETUP


@log_func
async def save_meetup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    team_sizes = parse_team_sizes(update.message.text)

    try:
        create_meetup(
            date_time=context.chat_data["date_time"],
            location=context.chat_data["location"],
            possible_team_sizes=team_sizes,
        )
    except MeetupDateAlreadyUsed:
        return await finish_conversation(
            update,
            "The meetup date and time is already in use. Please, restart the meetup creation.",
        )

    return await finish_conversation(
        update, f"Se ha creado la convocatoria para {context.chat_data['date_time']}"
    )


def parse_team_sizes(string_team_sizes: str) -> Tuple[str, ...]:
    return (int(size.strip()) for size in string_team_sizes.split(","))


@log_func
async def cancel_meetup_creation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update, "Creación de convocatoria cancelada.")
