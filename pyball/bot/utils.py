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

"""Utility functions."""
import argparse
import datetime
import functools
import re

from typing import Any, Callable, Dict, List, NamedTuple, Optional, Union

from telegram import Bot, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from pyball.bot.errors import (
    BotCommandError,
    BotExpectedMessageIdError,
    BotMachError,
    BotNoCallUpError,
    BotPlayerError,
)
from pyball.bot.globals import CALL_UP_KEYBOARD
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    CallUpMatchNotYetCreatedError,
    CallUpMatchWrongPlayersNumberError,
    CallUpPlayerDoesNotExistError,
    CallUpStatisticOfNonPlayers,
)
from pyball.callup.match import MatchStats
from pyball.db.errors import (
    DbPlayerAlreadyExistentError,
    DbStatisticForPlayerInMatchAlreadyExistent,
)
from pyball.db.utils import create_player, format_match_list, get_player_list
from pyball.logger import PYBALL_LOGGER
from pyball.settings import ADMINS_IDS


class CommandArgument(NamedTuple):
    """Parser simple argument."""

    name: str
    metavar: Optional[Union[str, tuple]] = None
    action: Union[str, argparse.Action] = "store"
    nargs: Optional[Union[int, str]] = None


class SubCommand(NamedTuple):
    """A subcommand that can contain multiple arguments and a callable."""

    names: List[str]
    arguments: List[CommandArgument] = []
    callable: Callable = None


class PlayerStatInput(NamedTuple):
    """Input object for palyer stats from the bot message."""

    name: str
    goals: int
    assists: int


class MatchStatValidator(argparse.Action):
    """Validate a result entry."""

    def __call__(self, _, namespace, values, option_string=None):
        """Add new values to the match stats object."""
        stats: MatchStats = getattr(namespace, self.dest, None) or MatchStats()

        try:
            stats.add_stat(values[0], int(values[1]), int(values[2]))
        except ValueError:
            raise argparse.ArgumentError(self, f"Stats: {values} are not valid")

        setattr(namespace, self.dest, stats)


class CommandParser(argparse.ArgumentParser):
    """ArgumentParser class to avoid printing help, just raise an error with the usage."""

    def print_help(self, _=None):
        """Raise an error with the help."""
        raise BotCommandError(f"```{self.format_help()}```")

    def error(self, _=None):
        """Raise an error with the usage."""
        raise BotCommandError(f"```{self.format_usage()}```")


def parse_command(command: str, subcommands: List[SubCommand], text: str) -> Dict[str, Any]:
    """Create a simple parser for the commands.

    :param command: The command string used in Telegram.
    :param subcommands: The lists of subcommands with arguments to add to the parser.
    :param text: The input string with the command in it.
    :returns: The parsed namespace.

    """
    parser = CommandParser(command)
    subparsers = parser.add_subparsers()

    for subcommand in subcommands:
        subparser = subparsers.add_parser(subcommand.names[0], aliases=subcommand.names[1:])

        for argument in subcommand.arguments:
            extra_args = {}
            if argument.metavar:
                extra_args["metavar"] = argument.metavar
            if argument.nargs:
                extra_args["nargs"] = argument.nargs
            subparser.add_argument(argument.name, action=argument.action, **extra_args)

        if subcommand.callable:
            subparser.set_defaults(func=subcommand.callable)

    try:
        string_input = text.split(" ", 1)[1].strip()
    except IndexError:
        parser.error()

    return vars(parser.parse_args(__split_without_splitting_quotes(string_input)))


__RE_NO_QUOTES_SPLIT = re.compile(r'(?:".*?"|\S)+')
"""Regex pattern to find words and quoted words."""


def __split_without_splitting_quotes(text: str) -> List[str]:
    """Split the string by words respecting the quoted substrings.

    :param text: The string to split.
    :returns: The list of words.

    """
    return [word.strip('"') for word in __RE_NO_QUOTES_SPLIT.findall(text)]


async def bot_call_message_function_with_keyboard(
    bot_message_function: Callable,
    text: str,
    *args,
    **kwargs,
) -> Message:
    """Call bot function with desired args and the call-up buttons.

    :param bot_message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    return await bot_call_message_function(
        bot_message_function=bot_message_function,
        text=text,
        reply_markup=CALL_UP_KEYBOARD,
        *args,
        **kwargs,
    )


async def bot_call_message_function(
    bot_message_function: Callable,
    text: str,
    *args,
    **kwargs,
) -> Message:
    """Call bot function with desired args.

    :param bot_message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    try:
        ret = await bot_message_function(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            *args,
            **kwargs,
        )
    except BadRequest as error:
        if "Message is not modified" in str(error):
            return
        raise
    return ret


def get_call_up(chat_data: dict) -> CallUp:
    """Get the call-up object.

    :param chat_data: Chat dictionary with the call-up object.
    :raise BotNoCallUpError: If no CallUp object has been found in the dictionary.

    """
    call_up = chat_data.get("call-up")

    if call_up is None:
        raise BotNoCallUpError(
            "Inicia una convocatoria antes de nada. No existe registro de la anterior."
        )

    return call_up


def validate_call_up_message_id(call_up: CallUp, reply_to_message: Optional[Message]):
    """Ensure the message identifier matches with the last call-up message.

    :param reply_to_message: The message the incommind command is replying to.
    :param expected_message_id: The message identifier of the last call-up.
    :raises BotExpectedMessageIdError: If the replied message id does not match with the last
        call-up.

    """
    if reply_to_message is None or not call_up.validate_message_id(
        str(reply_to_message.message_id)
    ):
        raise BotExpectedMessageIdError(
            "Responde al mensaje de la última convocatoria con el comando elegido."
        )


def ensure_admin(func):
    """Ensure the command is being executed by an admin."""

    @functools.wraps(func)
    async def wrapper_only_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the user executing the command is admin."""
        user_id = update.message.from_user.id

        if ADMINS_IDS and user_id not in ADMINS_IDS:
            PYBALL_LOGGER.debug(f"User {user_id} is not an admin ({ADMINS_IDS})")
            await update.message.reply_text("No tienes permisos para ejecutar este comando.")
            return

        PYBALL_LOGGER.debug(f"User {user_id} is an admin ({ADMINS_IDS})")

        return await func(update, context)

    return wrapper_only_admin


def get_command_argument(
    update_message_text: str,
    command_name: str,
    argument_name: str = "",
    argument_example: str = "",
    required: bool = False,
) -> str:
    """Parse the argument value from the update text.

    When the `requried` flag is on, this method will raise an error if no argument is provided. If
    the `required` flag is off and the argument is not found, this function will return an empty
    string.

    :param update_message_text: Full command string message.
    :param command_name: Name of the command to remove.
    :param argument_name: Name of the argumet to search for.
    :param argument_example: Example value
    :param required: If the argument is required or optional.
    :returns: The arugument value or an empty string.
    :raises BotCommandError: If the argument is required and it is not found.

    """
    argument: str = ""
    try:
        argument = update_message_text.split(None, 1)[1]
    except IndexError:
        if required:
            raise BotCommandError(command_name, argument_name, argument_example)

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
        PYBALL_LOGGER.debug(f"Sending search message {call_up}")
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
    remaining_players = call_up.remaining_players()

    substitutes_message_text = (
        "¡Hola compas! Estamos buscando suplentes para este partido.\n\nConvocatoria:"
        f" {call_up.title}\nJugadores restantes: {remaining_players}"
    )
    call_up_reply_message = "Mensaje de búsqueda actualizado."
    if remaining_players < 1:
        substitutes_message_text = (
            "¡Hola compas! Ya hemos llegado al cupo de personas convocadas, ¡muchas gracias!"
        )
        call_up_reply_message = (
            "Se han alcanzado las plazas necesarias. No se buscará más suplentes."
        )

    if call_up.is_searching():
        await bot_call_message_function(
            bot_message_function=bot.edit_message_text,
            text=substitutes_message_text,
            **call_up.subs_chat.as_dict(),
        )
        return call_up_reply_message

    call_up.set_subs_message_id(
        (
            await bot.send_message(
                text=substitutes_message_text,
                chat_id=call_up.subs_chat.chat_id,
            )
        ).message_id
    )
    return call_up_reply_message


def match_list(v: bool = False) -> str:
    """Retrieve the list of matches.

    :param v: Add verbose to the string.
    :returns: The formatted string.

    """
    return format_match_list()


def player_list() -> str:
    """Retrieve the list of players in the database.

    :returns: A formatted string containing the list.

    """
    return "\n".join(f"· `{p.name}`" for p in get_player_list())


def player_rank() -> str:
    """Retrieve the list of players in the database ordered by their rank.

    :returns: The ordered list of players.

    """
    ranking = sorted(get_player_list(), key=lambda p: p.skill, reverse=True)
    return "\n".join(f"{idx + 1:02} - `{p.name}`" for idx, p in enumerate(ranking))


def player_add(name: str, id: Optional[int]) -> str:
    """Create a new player in the database.

    :param name: Name of the new player.
    :param id: Identifier of the player.
    :returns: The confirmation of creation.

    """
    try:
        create_player(name, id)
    except DbPlayerAlreadyExistentError as error:
        raise BotPlayerError(f"El jugador {error.name} ya existe en la base de datos (o su id)")
    return f"Jugador `{name}` añadido con éxito"


async def callup_new(
    date: datetime.datetime, chat_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create a new call-up.

    :param date: Call-up date:
    :param chat_id: Chat identifier in which to send the call-up message.
    :param context: Information related to the bot and the chat.

    """
    chat_message_id = (
        await bot_call_message_function_with_keyboard(
            bot_message_function=context.bot.send_message,
            text=f"Lista de jugadores para la convocatoria *{date.strftime('%A %d/%m/%Y %H:%M')}*",
            chat_id=chat_id,
        )
    ).message_id

    context.chat_data["call-up"] = CallUp(date, chat_id, str(chat_message_id))


async def callup_add(
    name: str, context: ContextTypes.DEFAULT_TYPE, reply_function=Callable
) -> None:
    """Add a new player to the call-up.

    :param name: Player name.
    :param context: Information related to the bot and the chat.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    try:
        call_up.add_player(name)
    except CallUpPlayerDoesNotExistError as error:
        raise BotPlayerError(
            f"No se ha encontrado al jugador `{name}` en la base de datos."
        ) from error

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=reply_function,
        bot=context.bot,
    )


async def callup_del(
    name: str, context: ContextTypes.DEFAULT_TYPE, reply_function=Callable
) -> None:
    """Remove a player from the call-up.

    :param name: Player name.
    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    try:
        call_up.del_player(name)
    except CallUpPlayerDoesNotExistError as error:
        raise BotPlayerError(
            f"No se ha encontrado al jugador `{name}` en la base de datos."
        ) from error

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=reply_function,
        bot=context.bot,
    )


async def callup_search(
    stop: bool, context: ContextTypes.DEFAULT_TYPE, reply_function=Callable
) -> None:
    """Start the substitutes search.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    if call_up.is_searching() and stop:
        try:
            await context.bot.delete_message(**call_up.subs_chat.as_dict())
        except Forbidden as error:
            return await reply_function(
                "El bot no tiene los permisos suficientes para eliminar el mensaje del chat de"
                f" suplentes:\n\t{str(error)}",
            )

        call_up.set_subs_message_id(None)
        return await reply_function("Se ha detenido la búsqueda de suplentes.")

    if not stop:
        await search_substitutes(
            call_up=call_up,
            reply_function=reply_function,
            bot=context.bot,
            force=True,
        )


async def callup_teams(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create the teams.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    try:
        call_up.create_match()
    except CallUpMatchWrongPlayersNumberError as error:
        raise BotMachError(
            f"El número de jugadores apuntados (`{error.current_players}`) no es suficiente para"
            " crear 2 o 3 equipos."
        )

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )


async def callup_results(res: List[PlayerStatInput], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set the match results.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    try:
        call_up.set_results(res)
    except CallUpMatchNotYetCreatedError as error:
        raise BotMachError(
            "Aún no se han creado equipos para el partido actual. Envía /teams primero.",
        ) from error
    except CallUpStatisticOfNonPlayers as error:
        player_list = "\n".join(f"· {p}" for p in error.non_players)
        raise BotMachError(
            f"Ninguno de estos jugadores está apuntado en el partido:\n{player_list}", error.player
        ) from error
    except DbStatisticForPlayerInMatchAlreadyExistent as error:
        raise BotMachError(
            f"Las estadisticas de partido de {error.player.name} han sido previamente"
            f" guardadas para el partido {error.date}"
        ) from error

    await bot_call_message_function(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )

    await bot_call_message_function(
        bot_message_function=context.bot.send_message,
        text="Partido concluido!",
        chat_id=call_up.main_chat.chat_id,
        reply_to_message_id=call_up.main_chat.message_id,
    )

    await callup_search(
        stop=True,
        context=context,
        reply_function=context.bot.send_message,
    )

    del context.chat_data["call-up"]
