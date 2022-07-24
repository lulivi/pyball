# pylint: disable=unused-argument, wrong-import-position

# Copyright (c) 2022 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Bot to help organize game call-ups."""
import logging

from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Optional, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

from pyball.settings import BOT_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)


class PyBallError(Exception):
    """Base error for PyBall bot."""


class ExpectedMessageIdError(PyBallError):
    """When the message identifier is not the expected one."""


class PlayerAlreadyCalledUpError(PyBallError):
    """The player is already in the call-up."""


class PlayerNotCalledUpError(PyBallError):
    """The player hasn't been called-up."""


class PlayerParsingError(PyBallError):
    """The player name was not found in the message."""


class PlayerAction(Enum):
    """Represents the possible actions of a player."""

    JOIN = "join"
    LEAVE = "leave"

    def __str__(self) -> str:
        """Value of the enum member.

        :returns: The string object representation.

        """
        return self.value


class Players:
    """Simple class to manage the called players for a game.

    :ivar _players: The list of players.

    """

    __slots__ = ["_players"]

    def __init__(self):
        """Initialize the object."""
        self._players: Set[str] = set()

    def join(self, player_name) -> None:
        """Join the call-up.

        :param player_name: The player that wants to join the call-up.
        :raises PlayerAlreadyCalledUpError: If the player is already in the call-up list.

        """
        logger.debug(f"Trying to add the player `{player_name}`")

        if player_name in self._players:
            logger.debug(f"The player is already in the list")
            raise PlayerAlreadyCalledUpError(
                f"El jugador {player_name} ya está apuntado a esta convocatoria"
            )

        self._players.add(player_name)

    def leave(self, player) -> None:
        """Leave the call-up.

        :param player_name: The player that wants to leave the call-up.
        :raises PlayerNotCalledUpError: If the player is hasn't been called-up.

        """
        logger.debug(f"Trying to remove the player `{player}`")

        try:
            self._players.remove(player)
        except KeyError:
            logger.debug(f"The player is not in the list")
            raise PlayerNotCalledUpError(
                f"El jugador {player} no está apuntado a esta convocatoria"
            )

    def __str__(self) -> str:
        """List of players signed up for the call-up..

        :returns: The string representation of the players.

        """
        return "".join(
            [f"\n{index + 1} - {player}" for index, player in enumerate(sorted(self._players))]
        )


CALL_UP_KEYBOARD: InlineKeyboardMarkup = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Me apunto!!! :)", callback_data=str(PlayerAction.JOIN))],
        [InlineKeyboardButton("Me borro :(", callback_data=str(PlayerAction.LEAVE))],
    ]
)


def build_application() -> Application:
    """Create and build the bot application.

    :returns: the built application.

    """
    my_persistence = PicklePersistence(
        filepath=Path(__file__).resolve().parent.joinpath("bot.persistence")
    )

    application = Application.builder().token(BOT_TOKEN).persistence(my_persistence).build()

    application.add_handler(CommandHandler(("start", "help"), command_help))
    application.add_handler(CommandHandler("new", command_new))
    application.add_handler(CommandHandler("add", command_add))
    application.add_handler(CommandHandler("del", command_del))
    application.add_handler(CallbackQueryHandler(button_game))

    return application


async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    await update.message.reply_text(
        "¡Hola! Este bot puede ayudarte a organizar tu convocatoria.\n- Utiliza el comando /new"
        " para iniciar una nueva convocatoria o reiniciar la anterior.\n- Utiliza el comando /add"
        " <nombre> para añadir a una persona manualmente o /del <nombre> para eliminarla"
        " respondiendo al mensaje de la convocatoria."
    )


async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a new call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if "players" in context.chat_data:
        del context.chat_data["players"]

    context.chat_data["call_up_title"] = " ".join(update.message.text.split(" ")[1:])

    context.chat_data["message_id"] = (
        await update.message.reply_markdown(
            "Aún no hay nadie apuntado para la convocatoria"
            f" *{context.chat_data.get('call_up_title', '')}*",
            reply_markup=CALL_UP_KEYBOARD,
        )
    ).message_id


async def button_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manages the player actions of joning and leaving the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    query = update.callback_query

    if query.message.message_id != context.chat_data["message_id"]:
        await query.answer(
            text="Por favor, utiliza sólamente la última convocatoria. Esta está ya cerrada.",
        )
        return

    player = update.effective_user.full_name
    players = context.chat_data.get("players", Players())
    answer: Optional[str] = None

    actions: Dict[str, Callable] = {
        str(PlayerAction.JOIN): players.join,
        str(PlayerAction.LEAVE): players.leave,
    }

    try:
        actions[query.data](player)
    except PyBallError as error:
        answer = str(error)
        return
    finally:
        await query.answer(answer)

    await query.edit_message_text(
        text=(
            "Lista de jugadores para la convocatoria"
            f" *{context.chat_data.get('call_up_title', '')}*\n{str(players)}"
        ),
        reply_markup=CALL_UP_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    context.chat_data["players"] = players


async def command_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a new player to the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        validate_call_up_message_id(
            update.message.reply_to_message, context.chat_data["message_id"], "add"
        )
        player = extract_player_from_command(update.message.text, "add")
    except (ExpectedMessageIdError, PlayerParsingError) as error:
        await update.message.reply_text(str(error))
        return

    players = context.chat_data.get("players", Players())

    try:
        players.join(player)
    except PlayerAlreadyCalledUpError:
        return

    # context.bot.answer_callback_query
    await update.message.reply_to_message.edit_text(
        text=(
            "Lista de jugadores para la convocatoria"
            f" *{context.chat_data.get('call_up_title', '')}*\n{str(players)}"
        ),
        reply_markup=CALL_UP_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    context.chat_data["players"] = players


async def command_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a player from the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        validate_call_up_message_id(
            update.message.reply_to_message, context.chat_data["message_id"], "del"
        )
        player = extract_player_from_command(update.message.text, "del")
    except (ExpectedMessageIdError, PlayerParsingError) as error:
        await update.message.reply_text(str(error))
        return

    players = context.chat_data.get("players", Players())

    try:
        players.leave(player)
    except PlayerNotCalledUpError:
        return

    # context.bot.answer_callback_query
    await update.message.reply_to_message.edit_text(
        text=(
            "Lista de jugadores para la convocatoria"
            f" *{context.chat_data.get('call_up_title', '')}*\n{str(players)}"
        ),
        reply_markup=CALL_UP_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )
    context.chat_data["players"] = players


def validate_call_up_message_id(
    reply_to_message: Optional[Message], expected_message_id: str, command: str
):
    """Ensure the message identifier matches with the last call-up message.

    :param message: The target message of the update.
    :param expected_message_id: The message identifier of the last call-up.
    :raises:

    """
    if not reply_to_message or reply_to_message.message_id != expected_message_id:
        raise ExpectedMessageIdError(
            f"Responde al mensaje de la última convocatoria con el comando /{command} <nombre>."
        )


def extract_player_from_command(update_message_text: str, command: str) -> str:
    """Parses the player name from the update text.

    :param update: The event that caused the bot petition.
    :returns: The player name or None if no player is found

    """
    player = update_message_text.replace("@los_tensores_bot", "").replace(f"/{command} ", "")

    if not player:
        raise PlayerParsingError(
            f"Por favor, indica el usuario a continuación del comando: /{command} <nombre>. Por"
            f" ejemplo:\n\n\t/{command} antonio manuel"
        )

    return player
