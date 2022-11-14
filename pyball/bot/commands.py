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
import time

from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from pyball.bot.errors import (
    BotCommandError,
    BotExpectedMessageIdError,
    BotNoCallUpError,
    BotPlayerError,
)
from pyball.bot.utils import (
    CommandArgument,
    MatchStatValidator,
    SubCommand,
    bot_call_message_function,
    bot_call_message_function_with_keyboard,
    callup_add,
    callup_del,
    callup_new,
    callup_results,
    callup_search,
    callup_teams,
    ensure_admin,
    get_call_up,
    get_command_argument,
    match_list,
    parse_command,
    player_add,
    player_list,
    player_rank,
    search_substitutes,
    validate_call_up_message_id,
)
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.logger import PYBALL_LOGGER


async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    await bot_call_message_function(
        update.message.reply_text,
        "¡Hola! Este bot puede ayudarte a organizar tu convocatoria.\n\n- Utiliza el comando"
        " `/callup` para crear o interaccionar con la convocatoria.\n\n- Usa el comando `/player`"
        " para listar o añádir jugadores de la base de datos.\n\n- El comando `/match` te permite"
        " obtener informacion acerca de los partidos.",
    )


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

    player = update.effective_user.id
    answer: Optional[str] = None

    try:
        call_up.act(query.data, player)
    except (
        CallUpPlayerAlreadyCalledUpError,
        CallUpPlayerNotCalledUpError,
        CallUpPlayerDoesNotExistError,
    ) as error:
        answer = str(error)
        return
    finally:
        await query.answer(answer)

    await bot_call_message_function_with_keyboard(query.edit_message_text, str(call_up))
    await search_substitutes(
        call_up=call_up,
        reply_function=query.message.reply_text,
        bot=context.bot,
    )


@ensure_admin
async def command_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Match actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/match",
            subcommands=[
                SubCommand(["list", "l"], [CommandArgument("-v")], callable=match_list),
            ],
            text=update.message.text,
        )
    except BotCommandError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    output = args.pop("func")(**args)

    if output:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=output,
        )


@ensure_admin
async def command_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Player actions.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/player",
            subcommands=[
                SubCommand(["list", "l"], callable=player_list),
                SubCommand(["rank", "r"], callable=player_rank),
                SubCommand(
                    ["add", "a"],
                    [
                        CommandArgument("name", '"<nombre jugador>"'),
                        CommandArgument("-id", "<identifier>"),
                    ],
                    callable=player_add,
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
    except BotPlayerError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )

    if output:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=output,
        )


@ensure_admin
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
                    [CommandArgument("date", metavar='"<fecha>"')],
                    callable=functools.partial(
                        callup_new,
                        chat_id=update.message.chat_id,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["add", "a"],
                    [CommandArgument("name", metavar='"<nombre jugador>"')],
                    callable=functools.partial(
                        callup_add,
                        context=context,
                        reply_function=update.message.reply_text,
                    ),
                ),
                SubCommand(
                    ["del", "d"],
                    [CommandArgument("name", metavar='"<nombre jugador>"')],
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
                    callable=functools.partial(
                        callup_teams,
                        context=context,
                    ),
                ),
                SubCommand(
                    ["results", "r"],
                    [
                        CommandArgument(
                            "-res",
                            metavar=('"<nombre jugador>"', "<goles>", "<asistencias>"),
                            action=MatchStatValidator,
                            nargs=3,
                        )
                    ],
                    callable=functools.partial(
                        callup_results,
                        context=context,
                    ),
                ),
            ],
            text=update.message.text,
        )
        if "date" in args:
            args["date"] = datetime.datetime.strptime(args["date"], "%Y/%m/%d %H:%M")
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
                ' `"YYYY/MM/DD HH:MM"`.'
            ),
        )
        return

    try:
        await args.pop("func")(**args)
    except (CallUpPlayerAlreadyCalledUpError, CallUpPlayerNotCalledUpError):
        return
    except (BotPlayerError, BotNoCallUpError) as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return


@ensure_admin
async def command_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Call the new method periodically.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """

    def parse_next_date(day_hour: str) -> datetime.datetime:
        """Calculate the date for the first new command call.

        :param day_hour: A string containing the weekday and the time of the event.
        :returns: The date in which the callback will be called.

        """
        parsed_time: time.struct_time = time.strptime(day_hour.strip(), "%A %H:%M")
        today: datetime.datetime = datetime.datetime.today().astimezone()
        first_time: datetime.datetime = today.replace(
            hour=parsed_time.tm_hour,
            minute=parsed_time.tm_min,
            second=0,
            microsecond=0,
        ) + datetime.timedelta(days=parsed_time.tm_wday - today.weekday())

        if today > first_time:
            first_time += datetime.timedelta(weeks=1)

        PYBALL_LOGGER.debug(f"The first repeated call-up will be sent {first_time}")
        return first_time

    async def autonew(context: CallbackContext) -> None:
        """Create a new call-up with the given title.

        :param context: The information related to the update.

        """
        title = datetime.datetime.today().strftime(context.job.data["title"])
        PYBALL_LOGGER.debug(f"Creating an automated call-up: {title}")
        await callup_new(
            title=title,
            chat_id=context.job.data["chat_id"],
            context=context,
        )

    command_name = "repeat"
    argument_name = r"<día> <hora>: <título>"
    argument_example = r"Miércoles 21:00 - %A %Y/%m/%d"

    try:
        day_hour_title = get_command_argument(
            update_message_text=update.message.text,
            command_name=command_name,
            argument_name=argument_name,
            argument_example=argument_example,
            required=True,
        )
    except BotCommandError as error:
        await update.message.reply_text(str(error))
        return

    try:
        day_hour, title = day_hour_title.split("-", maxsplit=1)
        first_time: datetime.datetime = parse_next_date(day_hour)
        clean_title: str = title.strip()
    except ValueError:
        await update.message.reply_text(
            str(BotCommandError(command_name, argument_name, argument_example))
        )
        return

    context.job_queue.run_repeating(
        callback=autonew,
        interval=datetime.timedelta(days=7),
        first=first_time,
        data={"title": clean_title, "chat_id": str(update.message.chat_id)},
        name="Weekly call-up",
        chat_id=str(update.message.chat_id),
    )


@ensure_admin
async def command_stop_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the regular job.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    for job in context.job_queue.jobs():
        job.schedule_removal()
