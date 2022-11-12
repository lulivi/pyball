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
import re
import time

from typing import Optional

from telegram import Update
from telegram.error import Forbidden
from telegram.ext import CallbackContext, ContextTypes

from pyball.bot.errors import CommandError, ExpectedMessageIdError, NoCallUpError, NotAdminError
from pyball.bot.utils import (
    CommandArgument,
    bot_call_message_function,
    bot_call_message_function_with_keyboard,
    create_callup,
    ensure_admin,
    get_call_up,
    get_command_argument,
    parse_command,
    search_substitutes,
    split_without_splitting_quotes,
    validate_call_up_message_id,
)
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    MatchNotYetCreatedError,
    MatchWrongPlayersNumberError,
    PlayerAlreadyCalledUpError,
    PlayerDoesNotExistError,
    PlayerNotCalledUpError,
    StatisticOfNonPlayers,
)
from pyball.callup.match import MatchResults
from pyball.db.errors import PlayerAlreadyExistentError, StatisticForPlayerInMatchAlreadyExistent
from pyball.db.utils import create_player, get_player_list
from pyball.logger import PYBALL_LOGGER


async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    await bot_call_message_function(
        update.message.reply_text,
        "¡Hola! Este bot puede ayudarte a organizar tu convocatoria.\n\n- Utiliza el comando `/new"
        " <fecha y hora>` para iniciar una nueva convocatoria o reiniciar la anterior.\n\n-"
        " Utiliza el comando `/add <nombre>` para añadir a una persona manualmente o `/del"
        " <nombre>` para eliminarla respondiendo al mensaje de la convocatoria.\n\n- Utiliza el"
        " comando `/search` para buscar suplentes para el partido y `/stop_search` si una vez"
        " iniciada la búsqueda se quiere parar la actualización de jugadores y borrar el mensaje a"
        " los suplentes.\n\n- Usa el comando `/repeat <día> <hora>: <título>` para fijar un día en"
        " el que crear una convocatoria automáticamente. En el parámetro `<título>` se pueden"
        " utilizar los [códigos de"
        " formato](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)"
        " para formatear fechas. Por ejemplo, si se usa el comando\n`/repeat Miércoles 20:00 - %A"
        " %Y/%m/%d`\ncada miércoles a las 21h se crearía una encuesta con el título\n`<día de"
        " semana> <año>/<mes>/<día>`\npor ejemplo **Miércoles 2022/10/23**. Para cancelar la"
        " siguiente convocatoria automática usar `/stop_repeat`.",
    )


@ensure_admin
async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a new call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/new",
            arguments=[CommandArgument("date", "<fecha>")],
            text=update.message.text,
            single_arg=True,
        )
        call_up_date = datetime.datetime.strptime(args.date, "%Y/%m/%d %H:%M")
    except CommandError as error:
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

    await create_callup(call_up_date, str(update.message.chat_id), context)


async def button_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manages the player actions of joning and leaving the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    query = update.callback_query
    try:
        call_up: CallUp = get_call_up(context.chat_data)
        validate_call_up_message_id(call_up, query.message)
    except (NoCallUpError, ExpectedMessageIdError):
        await query.answer(
            text="Por favor, utiliza sólamente la última convocatoria. Ésta está ya cerrada.",
        )
        return

    player = update.effective_user.id
    answer: Optional[str] = None

    try:
        call_up.act(query.data, player)
    except (PlayerAlreadyCalledUpError, PlayerNotCalledUpError, PlayerDoesNotExistError) as error:
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
async def command_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a new player to the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
        args = parse_command(
            command="/add",
            arguments=[CommandArgument("name", "<nombre jugador>")],
            text=update.message.text,
            single_arg=True,
        )
    except (NoCallUpError, CommandError) as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        call_up.add_player(args.name)
    except PlayerAlreadyCalledUpError:
        return
    except PlayerDoesNotExistError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=f"No se ha encontrado al jugador `{args.name}` en la base de datos.",
        )
        return

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
    )


@ensure_admin
async def command_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a player from the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
        args = parse_command(
            command="/del",
            arguments=[CommandArgument("name", "<nombre jugador>")],
            text=update.message.text,
            single_arg=True,
        )
    except (NoCallUpError, CommandError, NotAdminError) as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        call_up.del_player(args.name)
    except PlayerNotCalledUpError:
        return
    except PlayerDoesNotExistError as error:
        update.message.reply_text(
            f"No se ha encontrado al jugador `{args.name}` en la base de datos."
        )
        return

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
    )


@ensure_admin
async def command_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for substitute players.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
    except NoCallUpError as error:
        await update.message.reply_text(str(error))
        return

    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
        force=True,
    )


@ensure_admin
async def command_stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the player search.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
    except NoCallUpError as error:
        await update.message.reply_text(str(error))
        return

    if not call_up.is_searching():
        return

    try:
        await context.bot.delete_message(**call_up.subs_chat.as_dict())
    except Forbidden as error:
        await bot_call_message_function(
            update.message.reply_text,
            "El bot no tiene los permisos suficientes para eliminar el mensaje del chat de"
            f" suplentes:\n\t{str(error)}",
        )
        return

    call_up.set_subs_message_id(None)
    await update.message.reply_text("Se ha detenido la búsqueda de suplentes.")


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
        """Callback wrapper to create a new call-up.

        :param context: The information related to the update.

        """
        title = datetime.datetime.today().strftime(context.job.data["title"])
        PYBALL_LOGGER.debug(f"Creating an automated call-up: {title}")
        await create_callup(
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
    except CommandError as error:
        await update.message.reply_text(str(error))
        return

    try:
        day_hour, title = day_hour_title.split("-", maxsplit=1)
        first_time: datetime.datetime = parse_next_date(day_hour)
        clean_title: str = title.strip()
    except ValueError:
        await update.message.reply_text(
            str(CommandError(command_name, argument_name, argument_example))
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


@ensure_admin
async def command_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List the available players.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    await bot_call_message_function(
        bot_message_function=update.message.reply_text,
        text="\n".join(f"· `{p.name}`" for p in get_player_list()),
    )


@ensure_admin
async def command_teams(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the last teams or create new ones.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
    except NoCallUpError as error:
        await update.message.reply_text(str(error))
        return

    try:
        call_up.create_match()
    except MatchWrongPlayersNumberError as error:
        await update.message.reply_text(
            f"El número de jugadores apuntados (`{error.current_players}`) no es suficiente para"
            " crear 2 o 3 equipos."
        )
        return

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )


async def command_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List the available players.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    ranking = sorted(get_player_list(), key=lambda p: p.skill, reverse=True)
    await bot_call_message_function(
        bot_message_function=update.message.reply_text,
        text="\n".join(f"{idx + 1} - `{p.name}`" for idx, p in enumerate(ranking)),
    )


@ensure_admin
async def command_set_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a match results.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        call_up: CallUp = get_call_up(context.chat_data)
    except NoCallUpError as error:
        await update.message.reply_text(str(error))
        return

    statistics = update.message.text.splitlines()[1:]
    match_results = MatchResults()

    for stat in statistics:
        try:
            name, str_goals, str_assists = stat.rsplit(" ", 2)
            goals = int(str_goals)
            assists = int(str_assists)
        except ValueError:
            await bot_call_message_function(
                bot_message_function=update.message.reply_text,
                text=(
                    "El formato no es correcto, introduce por línea: <nombre> <goles>"
                    " <asistencias>. Por ejemplo\n\n`Antonio Jesús 2 0`"
                ),
            )
            return
        match_results.add_stat(name, goals, assists)

    try:
        call_up.set_results(match_results)
    except MatchNotYetCreatedError:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text="Aún no se han creado equipos para el partido actual. Envía /teams primero.",
        )
        return
    except StatisticOfNonPlayers as error:
        player_list = "\n".join(f"· {p}" for p in error.non_players)
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=f"Ninguno de estos jugadores está apuntado en el partido:\n{player_list}",
        )
        return
    except StatisticForPlayerInMatchAlreadyExistent as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=(
                f"Las estadisticas de partido de {error.player.name} han sido previamente"
                f" guardadas para el partido {error.date}"
            ),
        )
        return

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

    del context.chat_data["call-up"]


@ensure_admin
async def command_create_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new player to the database.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        args = parse_command(
            command="/create_player",
            arguments=[
                CommandArgument("name", "<nombre jugador>"),
                CommandArgument("-id", "<identificador>"),
            ],
            text=update.message.text,
        )
    except CommandError as error:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=str(error),
        )
        return

    try:
        create_player(args.name, args.id)
    except PlayerAlreadyExistentError:
        await bot_call_message_function(
            bot_message_function=update.message.reply_text,
            text=f"El jugador `{args.name}` ya existe en la base de datos (o su id)",
        )
        return

    await bot_call_message_function(
        bot_message_function=update.message.reply_text,
        text=f"Jugador `{args.name}` añadido con éxito",
    )
