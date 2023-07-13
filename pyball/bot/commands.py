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

"""Bot commands and buttons."""

import datetime
import functools
import logging

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from pyball.__version__ import __version__
from pyball.bot.argument_parser import (
    ComaSeparatedMultiWordStringsAction,
    CommandArgument,
    MatchStatsAction,
    PlayerNameAction,
    SubCommand,
    parse_command,
)
from pyball.bot.errors import (
    BotCallUpError,
    BotCommandError,
    BotDatabaseError,
    BotMatchError,
    BotNotAdminError,
    BotPlayerError,
)
from pyball.bot.utils import (
    bot_call_message_function,
    bot_call_message_function_with_keyboard,
    callup_add,
    callup_del,
    callup_lock,
    callup_maximum,
    callup_new,
    callup_results,
    callup_search,
    callup_teams,
    callup_unlock,
    command_ensure_admin,
    ensure_admin,
    get_call_up,
    match_list,
    match_rollback,
    match_show,
    player_add,
    player_list,
    player_rank,
    player_reid,
    player_rename,
    search_substitutes,
    update_call_up_message,
)
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.logger import log_func
from pyball.settings import ADMINS_IDS, DATE_FORMAT, TIME_FORMAT

logger = logging.getLogger(__name__)


@log_func
async def command_version(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Show version of the application.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(update.message.reply_text, f"Pyball `{__version__}`")


@log_func
async def command_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(
        update.message.reply_text,
        (
            "¡Hola! Este bot puede ayudarte a organizar tu convocatoria.\n\n- Utiliza el comando"
            " `/callup` para crear o interaccionar con la convocatoria.\n\n- Usa el comando"
            " `/player` para listar o añádir jugadores de la base de datos.\n\n- El comando"
            " `/match` te permite obtener informacion acerca de los partidos.\n\nVersion:"
            f" `{__version__}`"
        ),
    )


@log_func
async def button_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage the player actions of joning and leaving the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    query = update.callback_query

    if query is None or query.data is None or query.message is None:
        return

    try:
        call_up: CallUp = get_call_up(query.message)
    except BotCallUpError as error:
        await query.answer(text=str(error))
        return

    if update.effective_user is None:
        return

    player = update.effective_user.id
    answer: str = ""

    old_call_up_yaml = call_up.as_yaml()

    try:
        call_up.act(query.data, player)
    except (
        CallUpMultiplePlayersFoundError,
        CallUpPlayerAlreadyCalledUpError,
        CallUpPlayerDoesNotExistError,
        CallUpPlayerNotCalledUpError,
    ) as error:
        answer = str(error)
        return
    finally:
        await query.answer(answer)

    await update_call_up_message(
        call_up=call_up,
        context=context,
        old_call_up_yaml=old_call_up_yaml,
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=query.message.reply_text,
        bot=context.bot,
    )


@log_func
async def command_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Match actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.effective_user is None:
        logger.error("No `effective_user` object in the command_match update")
        return

    if update.message is None:
        return

    try:
        args = parse_command(
            command="/match",
            subcommands=[
                SubCommand(
                    ["list", "l"],
                    callable=functools.partial(
                        match_list,
                        reply_function=update.message.reply_text,
                    ),
                ),
                SubCommand(
                    ["show", "s"],
                    [
                        CommandArgument(
                            "date",
                            metavar="DD/MMM/YYY",
                            help="Date of the match. E.g.: 10/oct/2023",
                        ),
                        CommandArgument(
                            "time", metavar="HH:MM", help="Time of the match. E.g.: 22:00"
                        ),
                    ],
                    callable=match_show,
                ),
                SubCommand(
                    ["rollback"], callable=ensure_admin(update.effective_user.id, match_rollback)
                ),
            ],
            text=update.message.text,
        )
        if "date" in args:
            parsed_time = datetime.datetime.strptime(args.pop("time"), TIME_FORMAT)
            args["date"] = datetime.datetime.strptime(args["date"], DATE_FORMAT).replace(
                hour=parsed_time.hour, minute=parsed_time.minute
            )
    except BotCommandError as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return
    except ValueError:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=(
                "La fecha del partido no es correcta. Por favor, indícala en formato"
                " DD/MMM/YYYY HH:MM."
            ),
        )
        return

    args["reply_function"] = update.message.reply_text

    try:
        output = await args.pop("func")(**args)
    except (BotNotAdminError, BotDatabaseError) as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return

    if output:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=output,
        )


@log_func
async def command_player(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Player actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.effective_user is None:
        logger.error("No `effective_user` object in the command_player update")
        return

    if update.message is None:
        return

    try:
        args = parse_command(
            command="/player",
            subcommands=[
                SubCommand(
                    ["list", "l"],
                    callable=player_list,
                ),
                SubCommand(
                    ["rank", "r"],
                    [
                        CommandArgument(
                            "order",
                            choices=["skill", "s", "points", "p", "goals", "g", "assists", "a"],
                            help="Order by [s]kill, [p]oints, [g]oals or [a]sists. Default goals.",
                            default="goals",
                        ),
                    ],
                    callable=player_rank,
                ),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument(
                            "name",
                            metavar="<nombre jugador>",
                            help="Player name",
                            action=PlayerNameAction,
                            nargs="+",
                        ),
                        CommandArgument("-id", "<identifier>", dest="identifier"),
                    ],
                    callable=ensure_admin(update.effective_user.id, player_add),
                ),
                SubCommand(
                    ["rename"],
                    [
                        CommandArgument(
                            "rename_list",
                            "<nombre jugador|id jugador>, <nuevo nombre>",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        ),
                    ],
                    callable=ensure_admin(update.effective_user.id, player_rename),
                ),
                SubCommand(
                    ["reid"],
                    [
                        CommandArgument(
                            "reid_list",
                            "<nombre jugador|id jugador>, <nuevo id>",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        ),
                    ],
                    callable=ensure_admin(update.effective_user.id, player_reid),
                ),
            ],
            text=update.message.text,
        )
    except BotCommandError as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        output = args.pop("func")(**args)
    except (BotPlayerError, BotNotAdminError) as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return

    if output:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=output,
        )


@log_func
@command_ensure_admin
async def command_callup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Call-up actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    new_subcommand_names = ["new", "n"]

    try:
        args = parse_command(
            command="/callup",
            subcommands=[
                SubCommand(
                    new_subcommand_names,
                    [
                        CommandArgument(
                            "-p",
                            metavar="<max players>",
                            type=int,
                            default=None,
                            dest="max_players",
                        ),
                        CommandArgument(
                            "-l",
                            metavar="<location>",
                            default=None,
                            dest="location",
                        ),
                        CommandArgument(
                            "date",
                            metavar="DD/MMM/YYY",
                            help="Date of the match. E.g.: 10/oct/2023",
                        ),
                        CommandArgument(
                            "time", metavar="HH:MM", help="Time of the match. E.g.: 22:00"
                        ),
                    ],
                    callable=functools.partial(
                        callup_new,
                        chat_id=update.message.chat_id,
                    ),
                ),
                SubCommand(
                    ["maximum", "m"],
                    [
                        CommandArgument(
                            "maximum",
                            metavar="<maximum> | auto",
                        )
                    ],
                    callable=callup_maximum,
                ),
                SubCommand(["lock", "l"], callable=callup_lock),
                SubCommand(["unlock", "u"], callable=callup_unlock),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument(
                            "names",
                            metavar="<nombre jugador>[, <nombre jugador>[, ...]]",
                            help="A coma separated list of player names",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        )
                    ],
                    callable=callup_add,
                ),
                SubCommand(
                    ["del", "d"],
                    [
                        CommandArgument(
                            "names",
                            metavar="<nombre jugador>[, <nombre jugador>[, ...]]",
                            help="A coma separated list of player names",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        )
                    ],
                    callable=callup_del,
                ),
                SubCommand(
                    ["search", "s"],
                    [CommandArgument("-stop", action="store_true")],
                    callable=callup_search,
                ),
                SubCommand(
                    ["teams", "t"],
                    [
                        CommandArgument(
                            "-swap",
                            metavar="<jugador a>, <jugador b>",
                            help="The two player names separated by coma",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        )
                    ],
                    callable=callup_teams,
                ),
                SubCommand(
                    ["results", "r"],
                    [
                        CommandArgument(
                            "stats",
                            help="Sucession of [g]oals and [assits] of the match",
                            metavar="g <nombre jugador 1> [a <nombre jugador 2>]",
                            action=MatchStatsAction,
                            nargs="+",
                        )
                    ],
                    callable=callup_results,
                ),
            ],
            text=update.message.text,
        )
        if "date" in args:
            parsed_time = datetime.datetime.strptime(args.pop("time"), TIME_FORMAT)
            args["date"] = datetime.datetime.strptime(args["date"], DATE_FORMAT).replace(
                hour=parsed_time.hour, minute=parsed_time.minute
            )
    except (BotCommandError, BotPlayerError) as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return
    except ValueError:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=(
                "La fecha de la nueva convocatoria no es correcta. Por favor, indícala en formato"
                " DD/MMM/YYYY HH:MM."
            ),
        )
        return

    if args["subcommand"] not in new_subcommand_names:
        try:
            args["call_up"] = get_call_up(update.message.reply_to_message)
        except BotCallUpError as error:
            await bot_call_message_function(
                message_function=update.message.reply_text,
                text=str(error),
            )
            return

    args["reply_function"] = update.message.reply_text
    args["context"] = context

    try:
        await args.pop("func")(**args)
    except (CallUpPlayerAlreadyCalledUpError, CallUpPlayerNotCalledUpError):
        return
    except (BotPlayerError, BotMatchError, BotCallUpError, BotNotAdminError) as error:
        await bot_call_message_function(
            message_function=update.message.reply_text,
            text=str(error),
        )
        return
    except TypeError as error:
        if error.args[0] == "call_up":
            await bot_call_message_function(
                message_function=update.message.reply_text,
                text=(
                    "No se ha encontrado una convocatoria en el mensaje respondido. Por favor,"
                    " responde al mensaje con la convocatoria."
                ),
            )
            return

    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.id)


@log_func
async def message_from_wrong_chat(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Message from wrong chat.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await update.message.reply_markdown_v2(
        "¡Hola\! Este bot está ejecutando el código alojado en"
        " [gitlab](https://gitlab.com/lulivi/pyball)\.\nÉchale un vistazo a la [introducción de la"
        " API]("
        "https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API)"
        " para crear tu bot\. Lee el README\.md en la raiz del repositorio\."
    )
