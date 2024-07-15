import logging

from enum import Enum, auto
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.logger import log_func
from pyballbot.player_telegram_id_translator import PlayerTelegramIdAlreadyInUse
from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.utils import bot_call_message_function


class CreatePlayerState(Enum):
    ENTER_PLAYER_TELEGRAM_ID = auto()
    ENTER_PLAYER_ROLE = auto()
    SAVE_PLAYER = auto()


class PlayerRole(Enum):
    REGULAR_PLAYER = "Player of the main team"
    SUBSTITUTE_PLAYER = "Substitute player"


player_role_to_bool: Dict[str, bool] = {
    PlayerRole.REGULAR_PLAYER.value: True,
    PlayerRole.SUBSTITUTE_PLAYER.value: False,
}


logger = logging.getLogger(__name__)


@log_func
async def ask_player_name(update: Update, _: ContextTypes.DEFAULT_TYPE) -> CreatePlayerState:
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
    context.chat_data["player_name"] = update.message.text.strip()

    await bot_call_message_function(
        update.message.reply_text,
        "Please, enter the player Telegram ID:",
    )

    return CreatePlayerState.ENTER_PLAYER_ROLE


@log_func
async def save_telegram_id_ask_role(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> CreatePlayerState:
    context.chat_data["telegram_id"] = update.message.text.strip()

    await bot_call_message_function(
        update.message.reply_text,
        "Is the player from the main team, or a substitute?:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[role.value] for role in PlayerRole],
            one_time_keyboard=True,
            input_field_placeholder="Player role",
        ),
    )

    return CreatePlayerState.SAVE_PLAYER


@log_func
async def save_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        player_requests.create(
            name=context.chat_data["player_name"],
            telegram_id=context.chat_data["telegram_id"],
            main=player_role_to_bool[update.message.text.strip()],
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
            update.message.reply_text,
            "The player name is already in use, introduce another one different.",
        )
    except CouldNotConnectToTheCore as error:
        return await finish_conversation(
            update.message.reply_text, f"There is a problem contacting Pyball core: {error}"
        )
    return await finish_conversation(update.message.reply_text, "Player created successfully.")


@log_func
async def cancel_player_creation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Player creation cancelled.")
