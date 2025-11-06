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

"""Argument parser classes and functions."""

import argparse
import datetime
import logging
import re

from typing import Any, Callable, Dict, List, NamedTuple, NoReturn, Optional, Type, Union

from pyball.legacy.bot.errors import BotCommandError, BotPlayerError
from pyball.legacy.bot.utils import md_monospace_items
from pyball.legacy.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerDoesNotExistError,
)
from pyball.legacy.callup.match import PlayersStatInput
from pyball.logger import log_func
from pyball.settings import DATETIME_FORMAT

logger = logging.getLogger(__name__)


class CustomHelpFormatter(argparse.HelpFormatter):
    """Ensure the help message arguments are properly formatted."""

    def format_help(self):
        """Format argument parser help."""
        formated_ussage = super().format_help()

        if "[<nombre jugador> ...]" in formated_ussage:
            formated_ussage = formated_ussage.replace("[<nombre jugador> ...]", "")

        if "[<nombre jugador>[, <nombre jugador>[, ...]] ...]" in formated_ussage:
            formated_ussage = formated_ussage.replace(
                "[<nombre jugador>[, <nombre jugador>[, ...]] ...]", ""
            )

        if "[<jugador a>, <jugador b> ...]" in formated_ussage:
            formated_ussage = formated_ussage.replace("[<jugador a>, <jugador b> ...]", "")

        return formated_ussage


class CommandArgument(NamedTuple):
    """Parser simple argument."""

    name: str
    help: Optional[str] = None
    metavar: Optional[Union[str, tuple]] = None
    action: Union[str, Type[argparse.Action]] = "store"
    default: Optional[Any] = None
    type: Optional[Any] = None
    choices: Optional[List[str]] = None
    nargs: Optional[Union[int, str]] = None
    dest: Optional[str] = None


class SubCommand(NamedTuple):
    """A subcommand that can contain multiple arguments and a callable."""

    names: List[str]
    arguments: List[CommandArgument] = []
    callable: Optional[Callable] = None
    check_admin_rights: Optional[int] = None


class MatchStatsAction(argparse.Action):  # pylint: disable=too-few-public-methods
    """Parse the match statistics."""

    def __call__(self, _, namespace, values, __=None) -> None:
        """Add new values to the match stats object."""
        stats: PlayersStatInput = PlayersStatInput()

        # Ensure there is at least one space before the first `g` for the proper splitting
        raw_stats_str = f" {' '.join(values)}"

        try:
            # person stats
            if " s " in raw_stats_str:
                for stat_line in raw_stats_str.split(" s ")[1:]:
                    parts = stat_line.strip().rsplit(" ", 2)
                    if not parts[1].isdigit():
                        parts[0] = f"{parts[0]} {parts[1]}"
                        del parts[1]
                    stats.add_player_stat(*parts)
            # goal stats
            else:
                # The first item will be empty since there is nothing at the left of the first `g`
                for raw_stat in raw_stats_str.split(" g ")[1:]:
                    stats.add_goal_stat(*raw_stat.split(" a "))
        except CallUpPlayerDoesNotExistError as error:
            raise BotPlayerError(
                f"No se ha encontrado al jugador `{error.player}` en la base de datos."
            ) from error
        except CallUpMultiplePlayersFoundError as error:
            raise BotPlayerError(
                f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
                f" {md_monospace_items(error.players)}. Por favor, concreta"
            ) from error

        setattr(namespace, self.dest, stats)


class MultiWordStringAction(argparse.Action):  # pylint: disable=too-few-public-methods
    """Transform a list of string into a single string."""

    def __call__(self, _, namespace, values, __=None) -> None:
        """Set the player name."""
        setattr(namespace, self.dest, " ".join(values))


class ComaSeparatedMultiWordStringsAction(
    argparse.Action
):  # pylint: disable=too-few-public-methods
    """Transform a list coma separated word groups list strings."""

    def __call__(self, _, namespace, values, __=None) -> None:
        """Set the player name."""
        elements = " ".join(values).split(",")
        setattr(
            namespace, self.dest, list(filter(None, [element.strip() for element in elements]))
        )


class CallupDateTimeAction(argparse.Action):  # pylint: disable=too-few-public-methods
    """Transform a list coma separated word groups list strings."""

    def __call__(self, _, namespace, values, __=None) -> None:
        """Set the player name."""
        try:
            setattr(
                namespace,
                self.dest,
                datetime.datetime.strptime(" ".join(values), DATETIME_FORMAT),
            )
        except ValueError as error:
            raise BotCommandError(f"La fecha '{values}' no tiene el formato adecuado.") from error


class CommandParser(argparse.ArgumentParser):
    """ArgumentParser class to avoid printing help, just raise an error with the usage."""

    def print_help(self, _=None) -> None:
        """Raise an error with the help."""
        raise BotCommandError(f"```\n{self.format_help()}```")

    def error(self, message=None) -> NoReturn:
        """Raise an error with the usage."""
        raise BotCommandError(f"{message}\n```\n{self.format_usage()}```")


@log_func
def parse_command(command: str, subcommands: List[SubCommand], text: str) -> Dict[str, Any]:
    """Create a simple parser for the commands.

    :param command: The command string used in Telegram.
    :param subcommands: The lists of subcommands with arguments to add to the parser.
    :param text: The input string with the command in it.
    :returns: The parsed namespace.

    """
    parser = CommandParser(command, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="subcommand")

    for subcommand in subcommands:
        subparser = subparsers.add_parser(
            subcommand.names[0],
            aliases=subcommand.names[1:],
            formatter_class=CustomHelpFormatter,
        )

        for argument in subcommand.arguments:
            extra_args: Dict[str, Union[str, tuple, int, List[str]]] = {}
            if argument.help is not None:
                extra_args["help"] = argument.help
            if argument.metavar is not None:
                extra_args["metavar"] = argument.metavar
            if argument.default is not None:
                extra_args["default"] = argument.default
            if argument.nargs is not None:
                extra_args["nargs"] = argument.nargs
            if argument.dest is not None:
                extra_args["dest"] = argument.dest
            if argument.type is not None:
                extra_args["type"] = argument.type
            if argument.choices is not None:
                extra_args["choices"] = argument.choices
            subparser.add_argument(
                argument.name,
                action=argument.action,
                **extra_args,  # type: ignore [arg-type]
            )

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
