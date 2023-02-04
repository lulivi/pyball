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
import functools

from typing import Callable, List, Optional, Union, cast

from telegram import Bot, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

from pyball.bot.errors import (
    BotExpectedMessageIdError,
    BotMatchError,
    BotNoCallUpError,
    BotNotAdminError,
    BotPlayerError,
)
from pyball.bot.globals import CALL_UP_KEYBOARD
from pyball.callup.callup import CallUp
from pyball.callup.errors import (
    CallUpMatchNotYetCreatedError,
    CallUpMatchWrongPlayersNumberError,
    CallUpMultiplePlayersFoundError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayersNotInMatch,
)
from pyball.callup.match import PlayersStatInput
from pyball.db.errors import (
    DbPlayerAlreadyExistentError,
    DbStatisticForPlayerInMatchAlreadyExistent,
)
from pyball.db.utils import create_player, format_match_list, get_player_list
from pyball.logger import PYBALL_LOGGER, log_func
from pyball.settings import ADMINS_IDS
from pyball.db import wrapper


def md_monospace_items(items: List[str]) -> str:
    """Transform a list of elements into a string of comma separated monospaced strings.

    :returns: The result string.

    """
    return f"`{'`, `'.join(items)}`"


@log_func
async def bot_call_message_function_with_keyboard(
    bot_message_function: Callable,
    text: str,
    *args,
    **kwargs,
) -> Union[bool, Message]:
    """Call bot function with desired args and the call-up buttons.

    :param bot_message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    return await bot_call_message_function(
        bot_message_function,
        text,
        reply_markup=CALL_UP_KEYBOARD,
        *args,
        **kwargs,
    )


@log_func
async def bot_call_message_function(
    bot_message_function: Callable,
    text: str,
    *args,
    **kwargs,
) -> Union[bool, Message]:
    """Call bot function with desired args.

    :param bot_message_function: Bot method that will be called to send or update a message.
    :param text: The string to send.
    :returns: The message sent or edited.

    """
    try:
        return await bot_message_function(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            *args,
            **kwargs,
        )
    except BadRequest as error:
        if "Message is not modified" in str(error):
            return False
        raise


def get_call_up(chat_data: Optional[dict]) -> CallUp:  # skip the optional check
    """Get the call-up object.

    :param chat_data: Chat dictionary with the call-up object.
    :raise BotNoCallUpError: If no CallUp object has been found in the dictionary.

    """
    call_up = chat_data.get("call-up")  # type: ignore [union-attr]

    if call_up is None:
        raise BotNoCallUpError(
            "Inicia una convocatoria antes de nada. No existe registro de la anterior."
        )

    return call_up


def validate_call_up_message_id(call_up: CallUp, reply_to_message: Message):
    """Ensure the message identifier matches with the last call-up message.

    :param reply_to_message: The message the incommind command is replying to.
    :param expected_message_id: The message identifier of the last call-up.
    :raises BotExpectedMessageIdError: If the replied message id does not match with the last
        call-up.

    """
    PYBALL_LOGGER.debug("Checking if the call-up message id is valid...")
    if reply_to_message is None or not call_up.validate_message_id(reply_to_message.message_id):
        PYBALL_LOGGER.error(
            f"The current call-up id (`{call_up.main_chat.message_id}`) does not match the button"
            f" press (`{reply_to_message.message_id}`)"
        )
        raise BotExpectedMessageIdError(
            "Responde al mensaje de la última convocatoria con el comando elegido."
        )
    PYBALL_LOGGER.debug("Checking if the call-up message id is valid... OK")


def command_ensure_admin(func):
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


def ensure_admin(user_id: int, func: Callable):
    """Ensure the command is being executed by an admin."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Check the user executing the command is admin."""
        if ADMINS_IDS and user_id not in ADMINS_IDS:
            PYBALL_LOGGER.debug(f"User {user_id} is not an admin ({ADMINS_IDS})")
            raise BotNotAdminError("No tienes permisos para ejecutar este comando.")
        PYBALL_LOGGER.debug(f"User {user_id} is an admin ({ADMINS_IDS})")

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


@log_func
def match_list(verbose: bool = False) -> str:
    """Retrieve the list of matches.

    :param verbose: Add verbose to the string.
    :returns: The formatted string.

    """
    return format_match_list(verbose)


@log_func
def player_list() -> str:
    """Retrieve the list of players in the database.

    :returns: A formatted string containing the list.

    """
    return "\n".join(
        f"· `{player.name}`" for player in get_player_list()  # pylint: disable=not-an-iterable
    )


@log_func
def player_rank(order: str) -> str:
    """Retrieve the list of players in the database ordered.

    :param order: The order to rank the players.
    :returns: The ordered list of players.

    """

    def order_by_skill(player_list: List[wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}`"
            for player in sorted(player_list, key=lambda player: player.skill, reverse=True)
        ]

    def order_by_points(player_list: List[wrapper.Player]) -> List[str]:
        return [
            f"`{player_tuple[0]}` ({player_tuple[1]})"
            for player_tuple in sorted(
                ((player.name, player.wins * 3 + player.ties) for player in player_list),
                key=lambda player_tuple: player_tuple[1],
                reverse=True,
            )
        ]

    def order_by_goals(player_list: List[wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}` ({player.goals})"
            for player in sorted(player_list, key=lambda player: player.goals, reverse=True)
        ]

    def order_by_assists(player_list: List[wrapper.Player]) -> List[str]:
        return [
            f"`{player.name}` ({player.assists})"
            for player in sorted(player_list, key=lambda player: player.assists, reverse=True)
        ]

    player_list = get_player_list()
    rank_players_by = {
        "skill": order_by_skill,
        "s": order_by_skill,
        "points": order_by_points,
        "p": order_by_points,
        "goals": order_by_goals,
        "g": order_by_goals,
        "asists": order_by_assists,
        "a": order_by_assists,
    }

    return "\n".join(
        f"{idx + 1:02} - {player_name}"
        for idx, player_name in enumerate(rank_players_by[order](player_list))
    )


@log_func
def player_add(name: str, identifier: Optional[int]) -> str:
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
async def callup_new(
    date: datetime.datetime, chat_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create a new call-up.

    :param date: Call-up date:
    :param chat_id: Chat identifier in which to send the call-up message.
    :param context: Information related to the bot and the chat.

    """
    if context.chat_data is None:
        return

    chat_message_id = cast(
        Message,
        (
            await bot_call_message_function_with_keyboard(
                context.bot.send_message,
                text=f"Convocatoria: *{date.strftime('%A %Y/%m/%d %H:%M')}*",
                chat_id=chat_id,
            )
        ),
    ).message_id

    context.chat_data["call-up"] = CallUp(date, chat_id, chat_message_id)


@log_func
async def callup_lock(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lock the call-up removing the inline keyboard.

    :param context: Information related to the bot and the chat.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    await bot_call_message_function(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )


@log_func
async def callup_unlock(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unlock the call-up re-adding the inline keyboard.

    :param context: Information related to the bot and the chat.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )


@log_func
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
            f"No se ha encontrado al jugador `{error.player}` en la base de datos."
        ) from error
    except CallUpMultiplePlayersFoundError as error:
        raise BotPlayerError(
            f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
            f" {md_monospace_items(error.players)}. Por favor, concreta"
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


@log_func
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
            f"No se ha encontrado al jugador `{error.player}` en la base de datos."
        ) from error
    except CallUpMultiplePlayersFoundError as error:
        raise BotPlayerError(
            f"La búsqueda del jugador `{error.wild_card}` obtuvo múltiples resultados:"
            f" {md_monospace_items(error.players)}. Por favor, concreta"
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


@log_func
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
            await bot_call_message_function(
                bot_message_function=context.bot.edit_message_text,
                text="Partido concluido.",
                **call_up.subs_chat.as_dict(),
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
            await reply_function(
                (
                    "Ocurrió un error intentando actualizar el mensaje del chat de suplentes:"
                    f"\n\t{str(error)}"
                ),
            )

        call_up.set_subs_message_id(None)
        await reply_function("Se ha detenido la búsqueda de suplentes.")
        return

    if not stop:
        await search_substitutes(
            call_up=call_up,
            reply_function=reply_function,
            bot=context.bot,
            force=True,
        )


@log_func
async def callup_teams(swap: Optional[List[str]], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create the teams.

    :param context: The information related to the update.
    :param reply_function: Function used to send messages within this method.

    """
    call_up: CallUp = get_call_up(context.chat_data)

    if swap is None:
        try:
            call_up.create_match()
        except CallUpMatchWrongPlayersNumberError as error:
            raise BotMatchError(
                f"El número de jugadores apuntados (`{error.current_players}`) no es"
                " suficiente para crear 2 o 3 equipos."
            ) from error
    else:
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

    await bot_call_message_function_with_keyboard(
        bot_message_function=context.bot.edit_message_text,
        text=str(call_up),
        **call_up.main_chat.as_dict(),
    )


@log_func
async def callup_results(
    stats: PlayersStatInput, context: ContextTypes.DEFAULT_TYPE, reply_function=Callable
) -> None:
    """Set the match results.

    :param context: The information related to the update.

    """
    if context.chat_data is None:
        return

    call_up: CallUp = get_call_up(context.chat_data)

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
        reply_function=reply_function,
    )

    del context.chat_data["call-up"]
