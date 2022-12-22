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

from telegram import Update
from telegram.ext import ContextTypes

from pyball.__version__ import __version__
from pyball.bot.argument_parser import (
    CommandArgument,
    MatchStatsAction,
    PlayerNameAction,
    SubCommand,
    parse_command,
)
from pyball.bot.errors import (
    BotCommandError,
    BotExpectedMessageIdError,
    BotMatchError,
    BotNoCallUpError,
    BotNotAdminError,
    BotPlayerError,
)
from pyball.bot.utils import (
    bot_call_message_function,
    bot_call_message_function_with_keyboard,
    callup_add,
    callup_del,
    callup_lock,
    callup_new,
    callup_results,
    callup_search,
    callup_teams,
    callup_unlock,
    command_ensure_admin,
    ensure_admin,
    get_call_up,
    match_list,
    player_add,
    player_list,
    player_rank,
    search_substitutes,
    validate_call_up_message_id,
)
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.logger import PYBALL_LOGGER, log_func


@log_func
async def command_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
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
    try:
        call_up: CallUp = get_call_up(context.chat_data)
        validate_call_up_message_id(call_up, query.message)
    except (BotNoCallUpError, BotExpectedMessageIdError):
        await query.answer(
            text="Por favor, utiliza sólamente la última convocatoria. Ésta está ya cerrada.",
        )
        return

    if update.effective_user is None:
        return

    player = update.effective_user.id
    answer: str = ""

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

    await bot_call_message_function_with_keyboard(
        bot_message_function=query.edit_message_text,
        text=str(call_up),
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=query.message.reply_text,
        bot=context.bot,
    )


@log_func
async def command_match(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Match actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/match",
            subcommands=[
                SubCommand(
                    ["list", "l"],
                    [CommandArgument("-v", dest="verbose")],
                    callable=match_list,
                ),
            ],
            text=update.message.text,
        )
    except BotCommandError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        output = args.pop("func")(**args)
    except BotNotAdminError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    if output:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=output,
        )


@log_func
async def command_player(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Player actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.effective_user is None:
        PYBALL_LOGGER.error("No `effective_user` object in the command_player update")
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
                            choices=["points", "goals", "skill"],
                            help="Order by skill, points or goals. Default skill.",
                            default="skill",
                        ),
                    ],
                    callable=player_rank,
                ),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument(
                            "name", "<nombre jugador>", action=PlayerNameAction, nargs="+"
                        ),
                        CommandArgument("-id", "<identifier>", dest="identifier"),
                    ],
                    callable=ensure_admin(update.effective_user.id, player_add),
                ),
            ],
            text=update.message.text,
        )
    except BotCommandError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        output = args.pop("func")(**args)
    except (BotPlayerError, BotNotAdminError) as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    if output:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=output,
        )


@log_func
@command_ensure_admin
async def command_callup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Call-up actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/callup",
            subcommands=[
                SubCommand(
                    ["new", "n"],
                    [
                        CommandArgument("date", metavar="YYYY/MM/DD"),
                        CommandArgument("time", metavar="HH:MM"),
                    ],
                    callable=functools.partial(
                        callup_new,
                        chat_id=update.message.chat_id,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["lock", "l"],
                    callable=functools.partial(
                        callup_lock,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["unlock", "u"],
                    callable=functools.partial(
                        callup_unlock,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument(
                            "name",
                            metavar="<nombre jugador>",
                            action=PlayerNameAction,
                            nargs="+",
                        )
                    ],
                    callable=functools.partial(
                        callup_add,
                        context=context,
                        reply_function=update.message.reply_text,
                    ),
                ),
                SubCommand(
                    ["del", "d"],
                    [
                        CommandArgument(
                            "name",
                            metavar="<nombre jugador>",
                            action=PlayerNameAction,
                            nargs="+",
                        )
                    ],
                    callable=functools.partial(
                        callup_del,
                        context=context,
                        reply_function=update.message.reply_text,
                    ),
                ),
                SubCommand(
                    ["search", "s"],
                    [CommandArgument("-stop", action="store_true")],
                    callable=functools.partial(
                        callup_search,
                        context=context,
                        reply_function=update.message.reply_text,
                    ),
                ),
                SubCommand(
                    ["teams", "t"],
                    [CommandArgument("-swap", metavar=('"<jugador a>"', '"<jugador b>'), nargs=2)],
                    callable=functools.partial(
                        callup_teams,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["results", "r"],
                    [
                        CommandArgument(
                            "stats",
                            help="g <nombre jugador 1> [a <nombre jugador 2>]",
                            metavar="<match statistic>",
                            action=MatchStatsAction,
                            nargs="+",
                        )
                    ],
                    callable=functools.partial(
                        callup_results,
                        context=context,
                        reply_function=update.message.reply_text,
                    ),
                ),
            ],
            text=update.message.text,
        )
        if "date" in args:
            parsed_time = datetime.datetime.strptime(args.pop("time"), "%H:%M")
            args["date"] = datetime.datetime.strptime(args["date"], "%Y/%m/%d").replace(
                hour=parsed_time.hour, minute=parsed_time.minute
            )
    except BotCommandError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return
    except ValueError:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=(
                "La fecha de la nueva convocatoria no es correcta. Por favor, indícala en formato"
                " YYYY/MM/DD HH:MM."
            ),
        )
        return

    try:
        await args.pop("func")(**args)
    except (CallUpPlayerAlreadyCalledUpError, CallUpPlayerNotCalledUpError):
        return
    except (BotPlayerError, BotMatchError, BotNoCallUpError, BotNotAdminError) as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
