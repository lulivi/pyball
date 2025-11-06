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

import argparse
import datetime
import functools
import html
import json
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from pyball import __version__
from pyball.legacy.bot.argument_parser import (
    CallupDateTimeAction,
    ComaSeparatedMultiWordStringsAction,
    CommandArgument,
    MatchStatsAction,
    MultiWordStringAction,
    SubCommand,
    parse_command,
)
from pyball.legacy.bot.errors import (
    BotCallUpError,
    BotCommandError,
    BotDatabaseError,
    BotMatchError,
    BotNotAdminError,
    BotPlayerError,
)
from pyball.legacy.bot.utils import (
    CallUpWrapper,
    bot_call_message_function,
    calc_next_wednesday,
    callup_add,
    callup_del,
    callup_location,
    callup_lock,
    callup_maximum,
    callup_new,
    callup_random_twelve,
    callup_results,
    callup_search,
    callup_teams,
    callup_unlock,
    command_ensure_admin,
    ensure_admin,
    get_call_up,
    get_call_up_wrapper_from_date,
    handle_button_action,
    match_list,
    match_rollback,
    match_show,
    player_add,
    player_list,
    player_main,
    player_rank,
    player_reid,
    player_rename,
)
from pyball.legacy.callup.callup import CallUp
from pyball.legacy.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.legacy.callup.players import find_player
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

    if query is None or query.message is None or update.effective_user is None:
        return

    try:
        call_up_wrapper: CallUpWrapper = get_call_up(query.message)
    except BotCallUpError as error:
        await query.answer(text=str(error))
        return

    player = update.effective_user.id

    try:
        with call_up_wrapper.unwrap() as call_up:
            await handle_button_action(call_up, player, query, context)
    except BotCallUpError as error:
        await query.answer(text=str(error))
        return


@log_func
async def command_match(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Match actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.effective_user is None:
        logger.error("No `effective_user` object in the command_match update")
        return

    if update.message is None or update.message.text is None:
        return

    try:
        args = parse_command(
            command="/match",
            subcommands=[
                SubCommand(
                    ["list", "l"],
                    [
                        CommandArgument(
                            "--all-seasons", action="store_true", help="Show all-time matches"
                        )
                    ],
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

    if update.message is None or update.message.text is None:
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
                        CommandArgument(
                            "--all-seasons", action="store_true", help="Show all-time matches"
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
                            action=MultiWordStringAction,
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
                SubCommand(
                    ["main"],
                    [
                        CommandArgument(
                            "name",
                            metavar="<nombre jugador>",
                            help="Player name",
                            action=MultiWordStringAction,
                            nargs="+",
                        ),
                        CommandArgument(
                            "--main",
                            action=argparse.BooleanOptionalAction,
                        ),
                    ],
                    callable=ensure_admin(update.effective_user.id, player_main),
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
async def command_callup(  # pylint: disable=too-many-return-statements
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Call-up actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None or update.message.text is None:
        return

    new_subcommand_names = ["new", "n", "next"]
    call_up_date_metavar = "call_up_date"
    reply_function = update.message.reply_text

    try:
        args = parse_command(
            command="/callup",
            subcommands=[
                SubCommand(
                    ["new", "n"],
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
                            action=MultiWordStringAction,
                            nargs="+",
                        ),
                        CommandArgument(
                            "-t",
                            metavar="<team name>, <team name>, <team name>",
                            help="A coma separated list of team names",
                            default=None,
                            nargs="+",
                            action=ComaSeparatedMultiWordStringsAction,
                            dest="team_names",
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
                    ["next"],
                    [],
                    callable=functools.partial(
                        callup_new,
                        max_players=None,
                        location=None,
                        team_names=None,
                        date=calc_next_wednesday(),
                        chat_id=update.message.chat_id,
                    ),
                ),
                SubCommand(
                    ["maximum", "m"],
                    [
                        CommandArgument(
                            "maximum",
                            metavar="<maximum> | auto",
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_maximum,
                ),
                SubCommand(
                    ["location"],
                    [
                        CommandArgument(
                            "new_location",
                            metavar="<location>",
                            help="The new location",
                            action=MultiWordStringAction,
                            nargs="+",
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_location,
                ),
                SubCommand(
                    ["lock", "l"],
                    [
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_lock,
                ),
                SubCommand(
                    ["unlock", "u"],
                    [
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_unlock,
                ),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument(
                            "names",
                            metavar="<nombre jugador>[, <nombre jugador>[, ...]]",
                            help="A coma separated list of player names",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to select the players from",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
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
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to delete the players from",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_del,
                ),
                SubCommand(
                    ["search", "s"],
                    [
                        CommandArgument("-stop", action="store_true"),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to search players for",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
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
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to swap teams in",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_teams,
                ),
                SubCommand(
                    ["random12", "r12"],
                    [
                        CommandArgument(
                            "-shielded",
                            metavar="<nombre jugador>[, <nombre jugador>[, ...]]",
                            help="A coma separated list of player names",
                            action=ComaSeparatedMultiWordStringsAction,
                            nargs="+",
                            default=[],
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
                    ],
                    callable=callup_random_twelve,
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
                        ),
                        CommandArgument(
                            "-date",
                            dest=call_up_date_metavar,
                            help="The date of the call-up to ...",
                            action=CallupDateTimeAction,
                            nargs="+",
                        ),
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
            message_function=reply_function,
            text=str(error),
        )
        return
    except ValueError:
        await bot_call_message_function(
            message_function=reply_function,
            text=(
                "La fecha de la nueva convocatoria no es correcta. Por favor, indícala en formato"
                " DD/MMM/YYYY HH:MM."
            ),
        )
        return

    args["context"] = context

    # There is no call-up, we are creating a new one
    if args["subcommand"] in new_subcommand_names:
        try:
            await args.pop("func")(**args)
        except (BotCallUpError, BotNotAdminError) as error:
            await bot_call_message_function(
                message_function=reply_function,
                text=str(error),
            )
            return
        # await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.id)
        return

    args["reply_function"] = reply_function

    try:
        call_up_wrapper: CallUpWrapper = (
            get_call_up_wrapper_from_date(args.pop(call_up_date_metavar))
            if args.get(call_up_date_metavar) is not None
            else get_call_up(update.message.reply_to_message)
        )

        with call_up_wrapper.unwrap() as call_up:
            args["call_up"] = call_up

            try:
                await args.pop("func")(**args)
            except (CallUpPlayerAlreadyCalledUpError, CallUpPlayerNotCalledUpError):
                logger.warning("The player was or was not in the call-up")
                return
            except (BotPlayerError, BotMatchError, BotCallUpError, BotNotAdminError) as error:
                await bot_call_message_function(
                    message_function=reply_function,
                    text=str(error),
                )
                return
            except TypeError as error:
                if error.args[0] == "call_up":
                    await bot_call_message_function(
                        message_function=reply_function,
                        text=(
                            "No se ha encontrado una convocatoria en el mensaje respondido. Por"
                            " favor, responde al mensaje con la convocatoria."
                        ),
                    )
                    return
                await bot_call_message_function(
                    message_function=reply_function,
                    text=escape_markdown(f"Ha ocurrido un error: {error}"),
                )
                return

            await context.bot.delete_message(
                chat_id=update.message.chat_id, message_id=update.message.id
            )
    except BotCallUpError as error:
        await bot_call_message_function(
            message_function=reply_function,
            text=str(error),
        )


@log_func
async def message_from_wrong_chat(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Message from wrong chat.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await update.message.reply_markdown_v2(
        r"¡Hola\! Este bot está ejecutando el código alojado en"
        r" [gitlab](https://gitlab.com/lulivi/pyball)\.\nÉchale un vistazo a la [introducción"
        " de la API]("
        "https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API)"
        r" para crear tu bot\. Lee el README\.md en la raiz del repositorio\."
    )


@log_func
async def command_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the admins.

    :param update: The object that caused the exception.
    :param context: Error information.

    """
    if context.error is None:
        logger.error("Exception while handling an update. Counld not get any error information")
        return

    logger.error("Exception while handling an update:", exc_info=context.error)

    traceback_str = html.escape(
        "".join(
            traceback.format_exception(
                None,
                context.error,
                context.error.__traceback__,
            )
        )
    )

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = html.escape(
        json.dumps(
            update.to_dict() if isinstance(update, Update) else str(update),
            indent=2,
            ensure_ascii=False,
        )
    )
    update_message = f"<pre>update = {update_str}</pre>"
    error_message = f"<pre>{html.escape(traceback_str)}</pre>"

    for admin_id in ADMINS_IDS:
        await context.bot.send_message(
            chat_id=admin_id, text="An exception was raised while handling an update"
        )
        await context.bot.send_message(
            chat_id=admin_id, text=update_message, parse_mode=ParseMode.HTML
        )
        await context.bot.send_message(
            chat_id=admin_id, text=error_message, parse_mode=ParseMode.HTML
        )
