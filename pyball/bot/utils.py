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

from typing import Callable, List, NamedTuple, Optional

from telegram import Bot, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from pyball.bot.errors import CommandError, ExpectedMessageIdError, NoCallUpError
from pyball.bot.globals import CALL_UP_KEYBOARD
from pyball.callup.callup import CallUp
from pyball.logger import PYBALL_LOGGER
from pyball.settings import ADMINS_IDS


class CommandArgument(NamedTuple):
    """Parser simple argument."""

    name: str
    metavar: str


class CommandParser(argparse.ArgumentParser):
    """ArgumentParser class to avoid printing help, just raise an error with the usage."""

    def print_help(self, _=None):
        """Raises an error with the help."""
        raise CommandError(f"```{self.format_help()}```")

    def error(self, _):
        """Raises an error with the usage."""
        raise CommandError(f"```{self.format_usage()}```")


def parse_command(
    command: str, arguments: List[CommandArgument], text: str, single_arg: bool = False
) -> argparse.Namespace:
    """Create a simple parser for the commands.

    :param command: The command string used in Telegram.
    :param arguments: The lists of arguments to add to the parser.
    :param text: The input string.
    :returns: The parsed namespace.

    """
    parser = CommandParser(command)

    for argument in arguments:
        parser.add_argument(argument.name, metavar=argument.metavar)

    string_input = text.replace(command, "").strip()
    arg_list = [string_input] if single_arg else __split_without_splitting_quotes(string_input)

    return parser.parse_args(arg_list)


__RE_NO_QUOTES_SPLIT = re.compile('(?:".*?"|\S)+')
"""Regex pattern to find words and quoted words."""


def __split_without_splitting_quotes(text: str) -> List[str]:
    """Split the string by words respecting the quoted substrings.

    :param text: The string to split.
    :returns: The list of words.

    """
    return [word.strip('"') for word in __RE_NO_QUOTES_SPLIT.findall(text)]


async def create_callup(
    date: datetime.datetime, chat_id: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create a new call-up.

    :param date: Call-up date:
    :param chat_id: Chat identifier in which to send the call-up message.
    :param context: Information related to the bot and the chat.

    """
    call_up = CallUp(date, chat_id, chat_message_id)
    context.chat_data["call-up"] = call_up

    chat_message_id = (
        await bot_call_message_function_with_keyboard(
            bot_message_function=context.bot.send_message,
            text=str(call_up),
            chat_id=call_up.main_chat.chat_id,
        )
    ).message_id


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
    :raise NoCallUpError: If no CallUp object has been found in the dictionary.

    """
    call_up = chat_data.get("call-up")

    if call_up is None:
        raise NoCallUpError(
            "Inicia una convocatoria antes de nada. No existe registro de la anterior."
        )

    return call_up


def validate_call_up_message_id(call_up: CallUp, reply_to_message: Optional[Message]):
    """Ensure the message identifier matches with the last call-up message.

    :param reply_to_message: The message the incommind command is replying to.
    :param expected_message_id: The message identifier of the last call-up.
    :raises ExpectedMessageIdError: If the replied message id does not match with the last call-up.

    """
    if reply_to_message is None or not call_up.validate_message_id(
        str(reply_to_message.message_id)
    ):
        raise ExpectedMessageIdError(
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
    :raises CommandError: If the argument is required and it is not found.

    """
    argument: str = ""
    try:
        argument = update_message_text.split(None, 1)[1]
    except IndexError:
        if required:
            raise CommandError(command_name, argument_name, argument_example)

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
    call_up_reply_message = "Mensaje de búsqueda enviado."
    if remaining_players < 1:
        substitutes_message_text = (
            f"¡Hola compas! Ya hemos llegado al cupo de personas convocadas, ¡muchas gracias!"
        )
        call_up_reply_message = (
            "Se han alcanzado las plazas necesarias. No se buscará más suplentes."
        )

    if call_up.is_searching():
        await bot.edit_message_text(
            text=substitutes_message_text,
            **call_up.subs_chat,
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
