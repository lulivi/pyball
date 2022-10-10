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
import functools
import locale
import logging

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Final, Optional, Set

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PicklePersistence,
)

from pyball.settings import ADMINS_IDS, BOT_TOKEN, LOCALE, SUBSTITUTES_ID

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Set locale for sorting player names
locale.setlocale(locale.LC_ALL, LOCALE)


class PyBallError(Exception):
    """Base error for PyBall bot."""


class NotAdminError(PyBallError):
    """The user is not in the admin list."""


class NoCallUpError(PyBallError):
    """There is no created call-up."""


class ExpectedMessageIdError(PyBallError):
    """When the message identifier is not the expected one."""


class PlayerAlreadyCalledUpError(PyBallError):
    """The player is already in the call-up."""


class PlayerNotCalledUpError(PyBallError):
    """The player hasn't been called-up."""


class PlayerParsingError(PyBallError):
    """The player name was not found in the message."""


class CommandArgumentError(PyBallError):
    """The argument was not specified."""

    def __init__(self, command_name: str, argument_name: str, argument_example: str) -> None:
        self._command_name: str = command_name
        self._argument_name: str = argument_name
        self._argument_example: str = argument_example

    def __str__(self) -> str:
        return (
            f"Por favor, indica el {self._argument_name} a continuación del comando:"
            f" /{self._command_name} <{self._argument_name}>. Por"
            f" ejemplo:\n\n\t/{self._command_name} {self._argument_example}"
        )


class PlayerAction(Enum):
    """Represents the possible actions of a player."""

    JOIN = "join"
    LEAVE = "leave"

    def __str__(self) -> str:
        """Value of the enum member.

        :returns: The string object representation.

        """
        return self.value


CALL_UP_KEYBOARD: Final[InlineKeyboardMarkup] = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Me apunto!!! :)", callback_data=str(PlayerAction.JOIN))],
        [InlineKeyboardButton("Me borro :(", callback_data=str(PlayerAction.LEAVE))],
    ]
)


@dataclass
class ChatInfo:
    """Basic information needed from a chat.

    :ivar id: Chat identifier.
    :ivar msg: Call-up message identifier.

    """

    chat_id: str
    msg_id: Optional[str] = None


class Players:
    """Simple class to manage the called players for a game.

    :ivar __players: The list of players.
    :ivar _maximum: The max number to search player for.

    """

    __slots__ = ["__players", "__maximum"]

    def __init__(self):
        """Initialize the object."""
        self.__players: Set[str] = set()
        self.__maximum: int
        self.__compute_maximum()

    def remaining(self) -> int:
        """Get the remaining number of player necessary for the call-up.

        :returns: The difference between the maximum and the current number of players.

        """
        return self.__maximum - len(self)

    def join(self, player_name: str) -> None:
        """Join the call-up.

        :param player_name: The player that wants to join the call-up.
        :raises PlayerAlreadyCalledUpError: If the player is already in the call-up list.

        """
        logger.debug(f"Trying to add the player `{player_name}`")

        if player_name in self.__players:
            logger.debug(f"The player is already in the list")
            raise PlayerAlreadyCalledUpError(
                f"El jugador {player_name} ya está apuntado a esta convocatoria"
            )

        self.__players.add(player_name)
        self.__compute_maximum()

    def leave(self, player: str) -> None:
        """Leave the call-up.

        :param player_name: The player that wants to leave the call-up.
        :raises PlayerNotCalledUpError: If the player is hasn't been called-up.

        """
        logger.debug(f"Trying to remove the player `{player}`")

        try:
            self.__players.remove(player)
        except KeyError:
            logger.debug(f"The player is not in the list")
            raise PlayerNotCalledUpError(
                f"El jugador {player} no está apuntado a esta convocatoria"
            )
        self.__compute_maximum()

    def __compute_maximum(self) -> int:
        """Guess the maximum number of player based on the current one.

        :param n_signed__players: Number of signed players.
        :returns: The maximum number of players to search for.

        """
        self.__maximum = min(filter(lambda x: len(self) <= x, (10, 12, 15, 20, 25)), default=100)

    def __len__(self) -> int:
        """Obtain the number of players signed up for the call-up.

        :returns: The number of players signed up.

        """
        return len(self.__players)

    def __str__(self) -> str:
        """List of players signed up for the call-up.

        Since we don't want UTF-8 characters to mess up the sorting, we use the
        :func:`functools.cmp_to_key` function with the chosen locale.

        :returns: The string representation of the players.

        """
        sorted_players = sorted(self.__players, key=functools.cmp_to_key(locale.strcoll))
        sorted_players.extend(["?????"] * (self.__maximum - len(self.__players)))
        return "\n".join(
            [f"{index + 1:0>2} - {player}" for index, player in enumerate(sorted_players)]
        )


class CallUp:
    """Necessary information involving a match call-up.

    :ivar __title: Summary of the call-up.
    :ivar __main_chat: Info about the main chat post.
    :ivar __subs_chat: Info about the substitutes chat post.
    :ivar __players: Object containing the list of players.

    """

    __slots__ = ["__title", "__main_chat", "__subs_chat", "__players", "__actions"]

    def __init__(self, title: str, main_chat_id: str, main_chat_msg: str) -> None:
        self.__title: str = title
        self.__main_chat: ChatInfo = ChatInfo(main_chat_id, main_chat_msg)
        self.__subs_chat: ChatInfo = ChatInfo(SUBSTITUTES_ID)
        self.__players: Players = Players()
        self.__actions: Dict[str, Callable] = {
            str(PlayerAction.JOIN): self.add_player,
            str(PlayerAction.LEAVE): self.del_player,
        }

    @property
    def title(self) -> str:
        """Get the title of the call-up.

        :returns: The title string.

        """
        return self.__title

    @property
    def players(self) -> Players:
        """Get the list of players called-up.

        :returns: The player object for this call-up.

        """
        return self.__players

    @property
    def subs_chat(self) -> ChatInfo:
        """Get the substitutes chat information.

        :returns: Substitutes chat id and message id.

        """
        return self.__subs_chat

    def act(self, action: PlayerAction, player: str) -> None:
        """Act depending on the player action.

        :param action: Action of joining or leaving the CallUp.
        :param player: Name of the player.

        """
        self.__actions[str(action)](player)

    def set_subs_message_id(self, message_id: str) -> None:
        """Set the substitutes chat message identifier.

        :param message_id: The identifier of the substitutes search message.

        """
        self.__subs_chat.msg_id = message_id

    def remaining_players(self) -> int:
        """Return the number of remaining players for the call-up.

        :returns: Missing players.

        """
        return self.__players.remaining()

    def validate_message_id(self, request_message_id: str) -> bool:
        """Check if the requester message identifier matches with the main chat message id.

        :param request_message_id: The incomming message identifier.
        :returns: Whether the incomming message id is the same as the call-up message id.

        """
        return self.__main_chat.msg_id == request_message_id

    def is_searching(self) -> bool:
        """Check if the current call-up is searching for substitutes.

        :returns: Whether the call-up needs substitutes.

        """
        return self.__subs_chat.msg_id is not None

    def add_player(self, player_name: str) -> None:
        """Add player to the call-up.

        :param player_name: Name of the player who wants to join.

        """
        self.__players.join(player_name)

    def del_player(self, player_name: str) -> None:
        """Remove a player from the call-up.

        :param player_name: Name of the player who wants to leave.

        """
        self.__players.leave(player_name)


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
    application.add_handler(CommandHandler("search", command_search))
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
        " respondiendo al mensaje de la convocatoria.\n- Utiliza el comando /search para buscar"
        " suplentes para el partido."
    )


async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a new call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        title = get_command_argument(
            update.message.text, "new", "título de la convocatoria", "10/10/10 20h", True
        )
        ensure_admin(update.message.from_user.id)
    except (CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    chat_id = update.message.chat_id
    chat_message = (
        await update.message.reply_markdown(
            f"Lista de jugadores para la convocatoria *{title}*",
            reply_markup=CALL_UP_KEYBOARD,
        )
    ).message_id

    context.chat_data["call-up"] = CallUp(title, chat_id, chat_message)


async def button_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manages the player actions of joning and leaving the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    query = update.callback_query
    call_up: CallUp = context.chat_data.get("call-up")

    try:
        validate_call_up_message_id(call_up, query.message)
    except (NoCallUpError, ExpectedMessageIdError):
        await query.answer(
            text="Por favor, utiliza sólamente la última convocatoria. Ésta está ya cerrada.",
        )
        return

    player = update.effective_user.full_name
    answer: Optional[str] = None

    try:
        call_up.act(query.data, player)
    except (PlayerAlreadyCalledUpError, PlayerNotCalledUpError) as error:
        answer = str(error)
        return
    finally:
        await query.answer(answer)

    await edit_call_up_message(call_up, query.edit_message_text)

    await search_substitutes(
        call_up=call_up,
        reply_function=query.message.reply_text,
        bot=context.bot,
    )


async def command_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a new player to the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        player = get_command_argument(
            update_message_text=update.message.text,
            command_name="add",
            argument_name="player name",
            argument_example="Antonio Manuel",
            required=True,
        )
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    try:
        call_up.add_player(player)
    except PlayerAlreadyCalledUpError:
        return

    await edit_call_up_message(call_up, update.message.reply_to_message.edit_text)
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
    )


async def command_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a player from the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        player = get_command_argument(
            update_message_text=update.message.text,
            command_name="del",
            argument_name="player name",
            argument_example="Antonio Manuel",
            required=True,
        )
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    try:
        call_up.del_player(player)
    except PlayerNotCalledUpError:
        return

    await edit_call_up_message(call_up, update.message.reply_to_message.edit_text)
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.Bot,
    )


async def command_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for substitute players.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
        force=True,
    )


async def edit_call_up_message(call_up: CallUp, update_message_func: Callable) -> None:
    """Edit call-up message.

    :param call_up: Necessary information about the call-up.
    :param update_message_func: Method that will update the call-up message (using a button or a
        command).

    """
    await update_message_func(
        text=f"Lista de jugadores para la convocatoria *{call_up.title}*\n{str(call_up.players)}",
        reply_markup=CALL_UP_KEYBOARD,
        parse_mode=ParseMode.MARKDOWN,
    )


def validate_call_up_message_id(call_up: Optional[CallUp], reply_to_message: Optional[Message]):
    """Ensure the message identifier matches with the last call-up message.

    :param reply_to_message: The message the incommind command is replying to.
    :param expected_message_id: The message identifier of the last call-up.
    :raises ExpectedMessageIdError: If the replied message id does not match with the last call-up.

    """
    if call_up is None:
        raise NoCallUpError(
            "Inicia una convocatoria antes de nada. No existe registro de la anterior."
        )

    if reply_to_message is None or not call_up.validate_message_id(reply_to_message.message_id):
        raise ExpectedMessageIdError(
            "Responde al mensaje de la última convocatoria con el comando elegido."
        )


def ensure_admin(user_id: str) -> None:
    """Check if the user has the correct rights.

    :param user_id: User identifier.
    :raises NotAdminError: If the user is not in the admin list.

    """
    logger.debug(f"Checking if user {user_id} is in the admin list: {ADMINS_IDS}")
    if ADMINS_IDS and user_id not in ADMINS_IDS:
        raise NotAdminError("No tienes permisos para ejecutar este comando.")


def get_command_argument(
    update_message_text: str,
    command_name: str,
    argument_name: str = "",
    argument_example: str = "",
    required: bool = False,
) -> str:
    """Parses the argument value from the update text.

    When the `requried` flag is on, this method will raise an error if no argument is provided. If
    the `required` flag is off and the argument is not found, this function will return an empty
    string.

    :param update_message_text: Full command string message.
    :param command_name: Name of the command to remove.
    :param argument_name: Name of the argumet to search for.
    :param argument_example: Example value
    :param required: If the argument is required or optional.
    :returns: The arugument value or an empty string.
    :raises CommandArgumentError: If the argument is required and it is not found.

    """
    argument: str = ""
    try:
        argument = update_message_text.split(None, 1)[1]
    except IndexError:
        if required:
            raise CommandArgumentError(command_name, argument_name, argument_example)

    return argument


async def search_substitutes(
    call_up: CallUp,
    reply_function: Callable,
    bot: Bot,
    force: bool = False,
) -> None:
    """Perform a substitutes search.

    The search will not take place if it has not been forced before. This means, we will search
    for substitutes if the call-up's substittues message identifier is set.

    :param call_up: Necessary information about the current call-up.
    :param reply_function: The comunicator function that will send the feedback messages.
    :param bot: Object in charge of sending and editing messages in the substitutes chat.
    :param force: If True, this will ensure the search starts (if still not running).

    """
    if not force and not call_up.is_searching():
        return

    try:
        search_message = await update_substitutes_search(call_up, bot)
    except Forbidden as error:
        reply_function(
            "El bot no tiene los permisos suficientes para enviar el mensaje al chat de suplentes:"
            f"\n\t{str(error)}"
        )

    if search_message:
        await reply_function(search_message)


async def update_substitutes_search(call_up: CallUp, bot: Bot) -> str:
    """Search for substitutes in the substitutes chat.

    :param call_up: Object containing all the necessary information about the match, the players
        and the substitutes.
    :param bot: Main bot object necessary to send and edit messages in other chat.

    """
    remaining__players = call_up.remaining_players()

    substitutes_message_text = (
        "¡Hola compas! Estamos buscando suplentes para este partido.\n\nConvocatoria:"
        f" {call_up.title}\nJugadores restantes: {remaining__players}"
    )
    call_up_reply_message = "Mensaje de búsqueda enviado."
    if remaining__players < 1:
        substitutes_message_text = (
            f"¡Hola compas! Ya hemos llegado al cupo de personas convocadas, ¡muchas gracias!"
        )
        call_up_reply_message = (
            "Se han alcanzado las plazas necesarias. No se buscará más suplentes."
        )

    if call_up.is_searching():
        await bot.edit_message_text(
            text=substitutes_message_text,
            chat_id=call_up.subs_chat.chat_id,
            message_id=call_up.subs_chat.msg_id,
        )
        return call_up_reply_message

    call_up.set_subs_message_id(
        (
            await bot.send_message(
                chat_id=call_up.subs_chat.chat_id,
                text=substitutes_message_text,
            )
        ).message_id
    )
    return call_up_reply_message
