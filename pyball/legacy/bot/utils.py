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
import datetime
import difflib
import functools
import locale
import logging

from typing import Callable, List, Optional, cast

from telegram import Bot, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from pyball.legacy import db
from pyball.legacy.bot.errors import (
    BotCallUpError,
    BotDatabaseError,
    BotMatchError,
    BotNotAdminError,
    BotPlayerError,
)
from pyball.legacy.bot.globals import CALL_UP_KEYBOARD
from pyball.legacy.callup.callup import CallUp
from pyball.legacy.callup.errors import (
    CallUpMatchAlreadyFinishedError,
    CallUpMatchNotYetCreatedError,
    CallUpMatchWrongPlayersNumberError,
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
    CallUpPlayersNotInMatch,
    CallUpWrongFormatError,
)
from pyball.legacy.callup.match import Match, PlayersStatInput
from pyball.legacy.db.errors import (
    DbMatchStatisticsNotFoundError,
    DbMultiplePlayersFoundError,
    DbNoBackUpError,
    DbPlayerAlreadyExistentError,
    DbPlayerNotFoundError,
    DbStatisticForPlayerInMatchAlreadyExistent,
)
from pyball.legacy.db.utils import (
    create_player,
    get_match,
    get_matches_date_list,
    get_player_list,
    reid_player,
    rename_player,
    rollback_database,
)
from pyball.logger import log_func
from pyball.settings import ADMINS_IDS, DATETIME_FORMAT

logger = logging.getLogger(__name__)


def md_monospace_items(items: List[str]) -> str:
    """Transform a list of elements into a string of comma separated monospaced strings.

    :returns: The result string.

    """
    return f"{', '.join([f'`{item}`' for item in items])}"


@log_func
async def bot_call_message_function(
    message_function: Callable,
    text: str,
    *args,
    with_keyboard: bool = False,
    **kwargs,
) -> Message:
    """Call bot function with desired args.

    :param message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    reply_markup = None
    if with_keyboard:
        reply_markup = CALL_UP_KEYBOARD

    return await message_function(
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        *args,
        **kwargs,
    )


def get_call_up(message: Optional[Message]) -> CallUp:
    """Get the call-up object.

    :param message: The call-up message.
    :raise BotCannotCreateCallupObject: If no CallUp object has been found in the message or if it
        contains errors.

    """
    if message is None or message.text is None:
        raise BotCallUpError("El comando debe responder a una convocatoria abierta")

    try:
        return CallUp.from_yaml(
            message.text,
            message.chat_id,
            message.id,
        )
    except CallUpWrongFormatError as error:
        raise BotCallUpError(
            f"El mensaje de convocatoria necesita el elemento `{error.missing_key}`"
        ) from error
    except CallUpMatchAlreadyFinishedError as error:
        raise BotCallUpError("El partido seleccionado ha concluido") from error


def command_ensure_admin(func):
    """Ensure the command is being executed by an admin."""

    @functools.wraps(func)
    async def wrapper_only_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the user executing the command is admin."""
        if update.message is None or update.message.from_user is None:
            return

        user_id = update.message.from_user.id

        if ADMINS_IDS and user_id not in ADMINS_IDS:
            logger.debug(f"User {user_id} is not an admin ({ADMINS_IDS})")
            await update.message.reply_text("No tienes permisos para ejecutar este comando.")
            return

        logger.debug(f"User {user_id} is an admin ({ADMINS_IDS})")

        return await func(update, context)

    return wrapper_only_admin


def ensure_admin(user_id: int, func: Callable):
    """Ensure the command is being executed by an admin."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Check the user executing the command is admin."""
        if ADMINS_IDS and user_id not in ADMINS_IDS:
            logger.debug(f"User {user_id} is not an admin ({ADMINS_IDS})")
            raise BotNotAdminError("No tienes permisos para ejecutar este comando.")
        logger.debug(f"User {user_id} is an admin ({ADMINS_IDS})")

        return func(*args, **kwargs)

    return wrapper


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
        logger.debug(f"Sending search message {call_up}")
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
        "¡Hola compas! Estamos buscando suplentes para este"
        f" partido.\n\n{call_up.title}\nJugadores restantes: *{remaining_players}*"
    )
    call_up_reply_message = "Mensaje de búsqueda actualizado."
    search_is_finished = False
    if remaining_players < 1:
        substitutes_message_text = (
            "¡Hola compas! Ya hemos llegado al cupo de personas convocadas, ¡muchas gracias!"
        )
        call_up_reply_message = (
            "Se han alcanzado las plazas necesarias. No se buscará más suplentes."
        )
        search_is_finished = True

    if call_up.is_searching():
        try:
            await bot_call_message_function(
                message_function=bot.edit_message_text,
                text=substitutes_message_text,
                **vars(call_up.subs_chat),
            )
        except BadRequest as error:
            if "Message is not modified" in str(error):
                pass
        if search_is_finished:
            call_up.reset_subs_message_id()
        return call_up_reply_message

    call_up.set_subs_message_id(
        (
            await bot_call_message_function(
                message_function=bot.send_message,
                text=substitutes_message_text,
                chat_id=call_up.subs_chat.chat_id,
            )
        ).message_id
    )
    return call_up_reply_message


async def update_call_up_message(
    call_up: CallUp,
    context: ContextTypes.DEFAULT_TYPE,
    with_keyboard: bool = True,
    old_call_up_yaml: Optional[str] = None,
) -> None:
    """Edit the call-up message with the new state.

    :param call_up: The call-up to show.
    :param context: The object from which get the edit_message method.
    :param with_keyboard: Whether to add a keyboard with join/leave to the message.
    :param old_call_up_yaml: The old call-up yaml string to create a diff with the new one. This
        diff is sent to all the admins.

    """
    try:
        await bot_call_message_function(
            message_function=context.bot.edit_message_text,
            text=str(call_up),
            with_keyboard=with_keyboard,
            **vars(call_up.main_chat),
        )
    except BadRequest as error:
        if "Message is not modified" in str(error):
            pass

    if old_call_up_yaml is not None:

        def diff_call_ups(old_call_up: str, new_call_up: str) -> str:
            diff_lines = list(
                difflib.unified_diff(old_call_up.splitlines(), new_call_up.splitlines(), n=20)
            )[4:]
            for idx, line in enumerate(diff_lines):
                if line.startswith(" "):
                    diff_lines[idx] = line.replace(" ", "  ", 1)
                    continue
                if line.startswith("+"):
                    diff_lines[idx] = line.replace("+", "+ ", 1)
                    continue
                if line.startswith("-"):
                    diff_lines[idx] = line.replace("-", "- ", 1)
            return "\n".join(diff_lines)

        call_up_diff = diff_call_ups(old_call_up_yaml, call_up.to_yaml())

        if call_up_diff:
            for admin_id in ADMINS_IDS:
                await bot_call_message_function(
                    message_function=context.bot.send_message,
                    chat_id=admin_id,
                    text=f"```{call_up_diff}```",
                )


@log_func
async def match_list(all_seasons: bool = False, reply_function=Callable, **_: dict) -> None:
    """Retrieve the list of matches.

    :param all_seasons: Whether to show the matches from the begining.
    :param reply_function: Function used to send messages within this method.

    """
    message = "\n".join(
        f"`{match.strftime(DATETIME_FORMAT)}`" for match in get_matches_date_list(all_seasons)
    )

    await bot_call_message_function(
        message_function=reply_function,
        text=message or "No se encontraron partidos esta temporada.",
    )


@log_func
async def match_show(
    date: datetime.datetime,
    reply_function=Callable,
    **_: dict,
) -> None:
    """Retrieve the list of matches.

    :param date: Date of the match to show.
    :param reply_function: Function used to send messages within this method.

    """
    try:
        await bot_call_message_function(
            message_function=reply_function,
            text=Match.from_dict(get_match(date)).to_yaml(),
        )
    except DbMatchStatisticsNotFoundError as error:
        raise BotDatabaseError(
            f"No se ha encontrado partido para la fecha `{date.strftime(DATETIME_FORMAT)}`"
        ) from error


@log_func
async def match_rollback(**_: dict) -> str:
    """Rollback to the last database state.

    :raises BotDatabaseError: When no database backup is found.
    :returns: A successfull message.

    """
    try:
        rollback_database()
    except DbNoBackUpError as error:
        raise BotDatabaseError(
            "No se ha encontrado una copia de seguridad de la base de datos."
        ) from error

    return "Recuperado último estado de la base de datos."


@log_func
def player_list(**_: dict) -> str:
    """Retrieve the list of players in the database.

    :returns: A formatted string containing the list.

    """
    return "\n".join(
        f"· `{name}`"
        for name in sorted(
            [player.name for player in get_player_list()], key=functools.cmp_to_key(locale.strcoll)
        )
    )


@log_func
def player_rank(order: str, all_seasons: bool = False, **_: dict) -> str:
    """Retrieve the list of players in the database ordered.

    :param all_seasons: Whether to show the statistics from all the seasons.
    :param order: The order to rank the players.
    :returns: The ordered list of players.

    """

    def order_by_skill(players: List[db.wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}`"
            for player in sorted(players, key=lambda player: player.skill, reverse=True)
        ]

    def order_by_points(players: List[db.wrapper.Player]) -> List[str]:
        return [
            f"`{player_tuple[0]}` ({player_tuple[1]})"
            for player_tuple in sorted(
                ((player.name, player.wins * 3 + player.ties) for player in players),
                key=lambda player_tuple: player_tuple[1],
                reverse=True,
            )
        ]

    def order_by_goals(players: List[db.wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}` ({player.goals})"
            for player in sorted(players, key=lambda player: player.goals, reverse=True)
        ]

    def order_by_assists(players: List[db.wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}` ({player.assists})"
            for player in sorted(players, key=lambda player: player.assists, reverse=True)
        ]

    players = get_player_list(all_seasons)
    rank_players_by = {
        "skill": order_by_skill,
        "s": order_by_skill,
        "points": order_by_points,
        "p": order_by_points,
        "goals": order_by_goals,
        "g": order_by_goals,
        "assists": order_by_assists,
        "a": order_by_assists,
    }

    player_ranking = "\n".join(
        f"{idx + 1:02} - {player_name}"
        for idx, player_name in enumerate(rank_players_by[order](players))
    )
    return f"Rank by {order}:\n{player_ranking}"


@log_func
def player_add(name: str, identifier: Optional[int], **_: dict) -> str:
    """Create a new player in the database.

    :param name: Name of the new player.
    :param identifier: Identifier of the player.
    :returns: The confirmation of creation.

    """
    try:
        create_player(name, identifier)
    except DbPlayerAlreadyExistentError as error:
        raise BotPlayerError(
            f"El jugador {error.name} ya existe en la base de datos (o su id)"
        ) from error
    return f"Jugador `{name}` añadido con éxito"


@log_func
def player_rename(rename_list: List[str], **_: dict) -> str:
    """Rename a player.

    :param player: Name or identifier of the player.
    :param new_name: New name of the player.
    :returns: The confirmation of creation.

    """
    if len(rename_list) != 2:
        raise BotPlayerError(
            "El comando solo espera un jugador y su nuevo nombre, separados por comas"
        )

    player, new_name = rename_list

    try:
        rename_player(player, new_name)
    except DbPlayerAlreadyExistentError as error:
        raise BotPlayerError(f"Ya existe el jugador `{error.name}` con ese nombre") from error
    except DbPlayerNotFoundError as error:
        raise BotPlayerError(
            f"No se ha encontrado al jugador `{error.wild_card}` en la base de datos."
        ) from error
    except DbMultiplePlayersFoundError as error:
        raise BotPlayerError(
            f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
            f" {md_monospace_items(error.players)}. Por favor, concreta"
        ) from error
    return f"Jugador `{player}` renombrado con éxito a `{new_name}`"


@log_func
def player_reid(reid_list: List[str], **_: dict) -> str:
    """Change a player ID.

    :param name: Name of the new player.
    :param identifier: Identifier of the player.
    :returns: The confirmation of creation.

    """
    if len(reid_list) != 2:
        raise BotPlayerError(
            "El comando solo espera un jugador y su nuevo ID, separados por comas"
        )

    player, new_identifier = reid_list

    try:
        reid_player(player, int(new_identifier))
    except DbPlayerAlreadyExistentError as error:
        raise BotPlayerError(f"Ya existe el jugador `{error.name}` con ese ID") from error
    except DbPlayerNotFoundError as error:
        raise BotPlayerError(
            f"No se ha encontrado al jugador `{error.wild_card}` en la base de datos."
        ) from error
    except DbMultiplePlayersFoundError as error:
        raise BotPlayerError(
            f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
            f" {md_monospace_items(error.players)}. Por favor, concreta"
        ) from error
    return f"Cambiada ID del jugador `{player}` con éxito"


@log_func
async def callup_new(
    max_players: Optional[int],
    location: Optional[str],
    team_names: Optional[str],
    date: datetime.datetime,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    **_: dict,
) -> None:
    """Create a new call-up.

    :param max_players: Max number of players by default in the call-up.
    :param location: The call-up location.
    :param date: Call-up date:
    :param chat_id: Chat identifier in which to send the call-up message.
    :param context: Information related to the bot and the chat.

    """
    chat_message_id = cast(
        Message,
        (
            await bot_call_message_function(
                message_function=context.bot.send_message,
                text="Creando convocatoria...",
                chat_id=chat_id,
                with_keyboard=True,
            )
        ),
    ).message_id

    call_up = CallUp(
        date=date,
        main_chat_id=chat_id,
        main_chat_msg=chat_message_id,
        location=location,
        fixed_player_number=max_players,
    )

    if team_names:
        team_name_list = [name.strip() for name in team_names.split(",")]
        call_up.save_team_names(team_names=team_name_list)

    await update_call_up_message(call_up=call_up, context=context)


@log_func
async def callup_maximum(
    maximum: str,
    context: ContextTypes.DEFAULT_TYPE,
    reply_function: Callable,
    call_up: CallUp,
    **_: dict,
) -> None:
    """Set the maximum call-up players to search.

    :param maximum: The maximum number of players to search. It can be `auto` or a number.
    :param context: Information related to the bot and the chat.
    :param reply_function: Function used to send messages within this method.

    """
    old_call_up_yaml = call_up.to_yaml()
    parsed_maximum: Optional[int] = None

    if maximum != "auto" and maximum.isnumeric():
        parsed_maximum = int(maximum)

    call_up.set_maximum(parsed_maximum)

    await search_substitutes(
        call_up=call_up,
        reply_function=reply_function,
        bot=context.bot,
    )
    await update_call_up_message(
        call_up=call_up,
        context=context,
        old_call_up_yaml=old_call_up_yaml,
    )


@log_func
async def callup_lock(context: ContextTypes.DEFAULT_TYPE, call_up: CallUp, **_: dict) -> None:
    """Lock the call-up removing the inline keyboard.

    :param context: Information related to the bot and the chat.

    """
    await update_call_up_message(call_up=call_up, context=context, with_keyboard=False)


@log_func
async def callup_unlock(context: ContextTypes.DEFAULT_TYPE, call_up: CallUp, **_: dict) -> None:
    """Unlock the call-up re-adding the inline keyboard.

    :param context: Information related to the bot and the chat.

    """
    await update_call_up_message(call_up=call_up, context=context)


@log_func
async def callup_add(
    names: List[str],
    context: ContextTypes.DEFAULT_TYPE,
    reply_function: Callable,
    call_up: CallUp,
    **_: dict,
) -> None:
    """Add new players to the call-up.

    :param names: List of player names to add to the call-up.
    :param context: Information related to the bot and the chat.
    :param reply_function: Function used to send messages within this method.

    """
    old_call_up_yaml = call_up.to_yaml()
    for name in names:
        try:
            call_up.add_player(name)
        except CallUpPlayerDoesNotExistError as error:
            raise BotPlayerError(
                f"No se ha encontrado al jugador `{error.player}` en la base de datos."
            ) from error
        except CallUpMultiplePlayersFoundError as error:
            raise BotPlayerError(
                f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
                f" {md_monospace_items(error.players)}. Por favor, concreta"
            ) from error
        except CallUpPlayerAlreadyCalledUpError:
            return

    await search_substitutes(
        call_up=call_up,
        reply_function=reply_function,
        bot=context.bot,
    )
    await update_call_up_message(
        call_up=call_up,
        context=context,
        old_call_up_yaml=old_call_up_yaml,
    )


@log_func
async def callup_del(
    names: List[str],
    context: ContextTypes.DEFAULT_TYPE,
    reply_function: Callable,
    call_up: CallUp,
    **_: dict,
) -> None:
    """Remove players from the call-up.

    :param names: List of player names to remove from the call-up.
    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    old_call_up_yaml = call_up.to_yaml()
    for name in names:
        try:
            call_up.del_player(name)
        except CallUpPlayerDoesNotExistError as error:
            raise BotPlayerError(
                f"No se ha encontrado al jugador `{error.player}` en la base de datos."
            ) from error
        except CallUpMultiplePlayersFoundError as error:
            raise BotPlayerError(
                f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
                f" {md_monospace_items(error.players)}. Por favor, concreta"
            ) from error
        except CallUpPlayerNotCalledUpError:
            pass

    await search_substitutes(
        call_up=call_up,
        reply_function=reply_function,
        bot=context.bot,
    )
    await update_call_up_message(
        call_up=call_up,
        context=context,
        old_call_up_yaml=old_call_up_yaml,
    )


@log_func
async def callup_search(
    stop: bool,
    context: ContextTypes.DEFAULT_TYPE,
    reply_function: Callable,
    call_up: CallUp,
    **_: dict,
) -> None:
    """Start the substitutes search.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    if call_up.is_searching() and stop:
        try:
            await bot_call_message_function(
                message_function=context.bot.edit_message_text,
                text="Partido concluido.",
                **vars(call_up.subs_chat),
            )
        except Forbidden as error:
            await reply_function(
                (
                    "El bot no tiene los permisos suficientes para actualizar el mensaje del chat"
                    f" de suplentes:\n\t{str(error)}"
                ),
            )
            return
        except BadRequest as error:
            if "Message is not modified" not in str(error):
                await reply_function(
                    (
                        "Ocurrió un error intentando actualizar el mensaje del chat de suplentes:"
                        f"\n\t{str(error)}"
                    ),
                )

        call_up.reset_subs_message_id()
        await reply_function("Se ha detenido la búsqueda de suplentes.")

    if not stop:
        await search_substitutes(
            call_up=call_up,
            reply_function=reply_function,
            bot=context.bot,
            force=True,
        )

    await update_call_up_message(call_up=call_up, context=context)


@log_func
async def callup_teams(
    swap: Optional[List[str]], context: ContextTypes.DEFAULT_TYPE, call_up: CallUp, **_: dict
) -> None:
    """Create the teams.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    old_call_up_yaml = call_up.to_yaml()
    if swap is None:
        try:
            call_up.create_match()
        except CallUpMatchWrongPlayersNumberError as error:
            raise BotMatchError(
                f"El número de jugadores apuntados (`{error.current_players}`) no es"
                " suficiente para crear 2 o 3 equipos."
            ) from error
    else:
        if len(swap) != 2:
            raise BotPlayerError("Se deben indicar dos jugadores para la opción `-swap`")
        try:
            call_up.match.swap_players(*swap)
        except CallUpMatchNotYetCreatedError as error:
            raise BotMatchError("El partido aun no ha sido creado") from error
        except CallUpPlayerDoesNotExistError as error:
            raise BotPlayerError(
                f"El jugador `{error.player}` no ha sido encontrado en la base de datos"
            ) from error
        except CallUpMultiplePlayersFoundError as error:
            raise BotPlayerError(
                f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
                f" {md_monospace_items(error.players)}. Por favor, concreta"
            ) from error
        except CallUpPlayersNotInMatch as error:
            raise BotMatchError(
                f"El jugador `{error.non_players[0]}` no está convocado"
            ) from error

    await update_call_up_message(
        call_up=call_up,
        context=context,
        old_call_up_yaml=old_call_up_yaml,
    )


@log_func
async def callup_results(
    stats: PlayersStatInput,
    context: ContextTypes.DEFAULT_TYPE,
    reply_function: Callable,
    call_up: CallUp,
    **_: dict,
) -> None:
    """Set the match results.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    old_call_up_yaml = call_up.to_yaml()
    try:
        call_up.set_results(stats)
    except CallUpMatchNotYetCreatedError as error:
        raise BotMatchError(
            "Aún no se han creado equipos para el partido actual. Envía /teams primero.",
        ) from error
    except CallUpPlayersNotInMatch as error:
        raise BotMatchError(
            "Ninguno de estos jugadores está apuntado en el partido:"
            f" {md_monospace_items(error.non_players)}"
        ) from error
    except CallUpPlayerDoesNotExistError as error:
        raise BotPlayerError(
            f"No se ha encontrado al jugador `{error.player}` en la base de datos."
        ) from error
    except CallUpMultiplePlayersFoundError as error:
        raise BotPlayerError(
            f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
            f" {md_monospace_items(error.players)}. Por favor, concreta"
        ) from error
    except DbStatisticForPlayerInMatchAlreadyExistent as error:
        raise BotMatchError(
            f"Las estadisticas de partido de {error.player} han sido previamente"
            f" guardadas para el partido {error.date}"
        ) from error

    await update_call_up_message(
        call_up=call_up,
        context=context,
        with_keyboard=False,
        old_call_up_yaml=old_call_up_yaml,
    )
    await bot_call_message_function(
        message_function=context.bot.send_message,
        text="Partido concluido!",
        chat_id=call_up.main_chat.chat_id,
        reply_to_message_id=call_up.main_chat.message_id,
    )
    await callup_search(
        stop=True,
        context=context,
        reply_function=reply_function,
        call_up=call_up,
    )
