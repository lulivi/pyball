import logging

from enum import Enum, auto
from typing import List

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyballbot.commands.finish_conversation import finish_conversation
from pyballbot.logger import log_func
from pyballbot.player_telegram_uuid_translator import PlayerTelegramIdAlreadyInUse
from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import (
    CouldNotConnectToTheCore,
    PlayerIdDoesNotExist,
    PlayerNameDoesNotExist,
    PlayerQueryError,
    PlayerUpdateError,
)
from pyballbot.requests.types import Player
from pyballbot.utils import bot_call_message_function


class RenamePlayerState(Enum):
    ASK_NEW_PLAYER_NAME = auto()
    UPDATE_PLAYER = auto()


logger = logging.getLogger(__name__)


@log_func
async def ask_player_name(update: Update, _: ContextTypes.DEFAULT_TYPE) -> RenamePlayerState:
    """Starts the conversation and asks the user about their gender."""
    all_players: List[Player] = sorted(player.name for player in player_requests.get_all())
    print("All players:", all_players)

    await bot_call_message_function(
        update.message.reply_text,
        "Please, enter the player name you want to rename. Press /cancel to stop the renaming:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[player_tuple for player_tuple in zip(all_players[::2], all_players[1::2])],
            one_time_keyboard=True,
            input_field_placeholder="Player selection",
        ),
    )

    return RenamePlayerState.ASK_NEW_PLAYER_NAME


@log_func
async def save_current_name_ask_new_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> RenamePlayerState:
    """Starts the conversation and asks the user about their gender."""
    context.chat_data["current_name"] = update.message.text.strip()

    await bot_call_message_function(
        update.message.reply_text,
        "Please, enter the new player name:",
    )

    return RenamePlayerState.UPDATE_PLAYER


@log_func
async def rename_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    finish_message: str = "Player renamed successfully."

    try:
        player_requests.rename(
            current_name=context.chat_data["current_name"],
            new_name=update.message.text.strip(),
        )
    except PlayerNameDoesNotExist as error:
        finish_message = (
            (
                f"Error renaming a player. The provided player name (`{error.name}`) does not"
                " exist. Please, click one of the buttons when renaming a player."
            ),
        )
    except (PlayerQueryError, PlayerIdDoesNotExist, PlayerUpdateError) as error:
        finish_message = (f"There was an error renaming the player. Please try again: {error}.",)
    except CouldNotConnectToTheCore as error:
        finish_message = f"There is a problem contacting Pyball core: {error}"

    return await finish_conversation(update.message.reply_text, finish_message)


@log_func
async def cancel_player_renaming(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    return await finish_conversation(update.message.reply_text, "Player renaming cancelled.")
