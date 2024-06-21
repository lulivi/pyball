import logging

from enum import Enum, auto

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyball.greenfield.player.infrastructure.bot_player import create_player
from pyball.greenfield.player.infrastructure.errors import PlayerTelegramIdInUse
from pyball.greenfield.utils.bot.commands.finish_conversation import finish_conversation
from pyball.logger import log_func


class CreatePlayerState(Enum):
    ENTER_PLAYER_TELEGRAM_ID = auto()
    SAVE_PLAYER = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_player_name(update: Update, _: ContextTypes.DEFAULT_TYPE) -> CreatePlayerState:
    """Starts the conversation and asks the user about their gender."""
    await update.message.reply_text(
        (
            "Por favor, introduce el nombre del nuevo jugador. Manda el comando /cancel para"
            " cancelar la creación de jugador."
        ),
        parse_mode=ParseMode.MARKDOWN,
    )

    return CreatePlayerState.ENTER_PLAYER_TELEGRAM_ID


@log_func
async def save_player_name_ask_telegram_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> CreatePlayerState:
    """Starts the conversation and asks the user about their gender."""
    context.chat_data["player_name"] = update.message.text.strip()

    await update.message.reply_text(
        "Por favor, introduce el ID de Telegram del nuevo jugador.",
        parse_mode=ParseMode.MARKDOWN,
    )

    return CreatePlayerState.SAVE_PLAYER


async def save_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        create_player(
            name=context.chat_data["player_name"], telegram_id=update.message.text.strip()
        )
    except PlayerTelegramIdInUse as error:
        await update.message.reply_text(
            (
                f"The player Telegram ID {error.telegram_id} is already in use, please introduce"
                " one that is not used:"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        return CreatePlayerState.SAVE_PLAYER

    return await finish_conversation(update, "Jugador creado con éxito.")


@log_func
async def cancel_player_creation(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update, "Creación de jugador cancelada.")
