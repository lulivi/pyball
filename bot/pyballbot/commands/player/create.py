import logging

from enum import Enum, auto

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.logger import log_func
from pyballbot.player_telegram_uuid_translator import (
    PlayerIdAlreadyInUse,
    PlayerTelegramIdAlreadyInUse,
)
from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.utils import bot_call_message_function


class CreatePlayerState(Enum):
    ENTER_PLAYER_TELEGRAM_ID = auto()
    SAVE_PLAYER = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_player_name(update: Update, _: ContextTypes.DEFAULT_TYPE) -> CreatePlayerState:
    """Starts the conversation and asks the user about their gender."""
    await bot_call_message_function(
        update.message.reply_text,
        "Por favor, introduce el nombre del nuevo jugador. Manda el comando /cancel para"
        " cancelar la creación de jugador.",
    )

    return CreatePlayerState.ENTER_PLAYER_TELEGRAM_ID


@log_func
async def save_player_name_ask_telegram_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> CreatePlayerState:
    """Starts the conversation and asks the user about their gender."""
    context.chat_data["player_name"] = update.message.text.strip()

    await bot_call_message_function(
        update.message.reply_text,
        "Please, enter the player Telegram ID:",
    )

    return CreatePlayerState.SAVE_PLAYER


@log_func
async def save_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        player_requests.create(
            name=context.chat_data["player_name"], telegram_id=update.message.text.strip()
        )
    except PlayerTelegramIdAlreadyInUse as error:
        await bot_call_message_function(
            update.message.reply_text,
            f"The player Telegram ID {error.telegram_id} is already in use, please introduce"
            " one that is not used:",
        )
        return CreatePlayerState.SAVE_PLAYER
    except player_requests.PlayerNameIsAlreadyInUse as error:
        return await finish_conversation(
            update, "The player name is already in use, introduce another one different."
        )
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update, f"There is a problem contacting Pyball core: {error}"
        )
    return await finish_conversation(update, "Jugador creado con éxito.")


@log_func
async def cancel_player_creation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update, "Creación de jugador cancelada.")
