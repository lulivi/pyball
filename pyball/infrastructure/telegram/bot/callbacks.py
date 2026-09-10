# Copyright (c) 2026 Luis Liñán
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
"""Inline button callback handler."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import telegram
from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram.bot.handlers.meetup import _do_search
from pyball.infrastructure.telegram.formatters import parse_callback_data
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.infrastructure.telegram.notifications import refresh_callup_messages
from pyball.logger import log_func

if TYPE_CHECKING:
    from pyball.application.notifier import MatchNotifier
    from pyball.domain.player.models import Player
    from pyball.infrastructure.telegram.settings import TelegramAppSettings

logger = logging.getLogger(__name__)


@log_func
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query
    if query is None or query.message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    notifier: "MatchNotifier" = context.bot_data["notifier"]

    callback_data = query.data
    if callback_data is None:
        await query.answer("Datos de acción no válidos.", show_alert=True)
        return

    parsed = parse_callback_data(callback_data)
    if not parsed:
        await query.answer("Datos de acción no válidos.", show_alert=True)
        return

    action, date_str = parsed
    meetup_date = _parse_meetup_date(date_str)
    if meetup_date is None:
        await query.answer("Formato de fecha no válido.", show_alert=True)
        return

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if not meetup:
        await query.answer("No se ha encontrado el meetup.", show_alert=True)
        return

    from_user = query.from_user
    if from_user is None:
        await query.answer("Usuario no identificado.", show_alert=True)
        return

    if action in ("join", "leave", "join_sub", "leave_sub"):
        mapping_store = TelegramMappingStore(
            settings.paths.data_dir / "bot" / "telegram-uuid.json"
        )
        await _handle_player_action(
            action,
            meetup,
            meetup_date,
            query,
            container,
            mapping_store,
            context.bot,
            settings,
            notifier,
        )
    elif action == "search":
        await _handle_search_callback(
            meetup, query, container, context.bot, settings, from_user.id
        )


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
async def _handle_player_action(
    action: str,
    meetup: Meetup,
    meetup_date: datetime,
    query: CallbackQuery,
    container: Container,
    mapping_store: TelegramMappingStore,
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    notifier: "MatchNotifier",
) -> None:
    """Handle join/leave/join_sub/leave_sub callback actions.

    The regular and substitute variants share behaviour, so membership and
    action branching is decided by substring matching (``"join" in action``
    matches both ``join`` and ``join_sub``). This is safe because the action
    set is constrained by ``parse_callback_data``.
    """
    if not meetup.is_signup_open():
        await query.answer(
            "Los equipos ya están hechos, no se puede apuntar ni salir del meetup.",
            show_alert=True,
        )
        return

    telegram_id = query.from_user.id

    player_id_str = mapping_store.get_player_id(telegram_id)
    if not player_id_str:
        await query.answer(
            "No tienes ningún jugador vinculado. Contacta con el administrador para registrarte.",
            show_alert=True,
        )
        return

    player_id = _validate_player_id(player_id_str)
    if not player_id:
        await query.answer(
            "Vinculación de jugador no válida. Contacta con el administrador.",
            show_alert=True,
        )
        return

    player = container.player_repository.find_by_id(player_id)
    if not player:
        await query.answer(
            "Jugador no encontrado. Contacta con el administrador.",
            show_alert=True,
        )
        return

    is_player_in_meetup = player_id in meetup.players
    if is_player_in_meetup and "join" in action:
        await query.answer("Ya estás unido a este meetup.", show_alert=True)
        return
    if not is_player_in_meetup and "leave" in action:
        await query.answer("No estás en este meetup.", show_alert=True)
        return

    modified = _process_action(action, meetup_date, player, container)
    if modified:
        updated_meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if updated_meetup:
            await refresh_callup_messages(bot, settings, container, updated_meetup)
            is_substitute = "_sub" in action
            if "join" in action:
                await notifier.on_player_joined(updated_meetup, player, is_substitute)
            else:
                await notifier.on_player_left(updated_meetup, player, is_substitute)
        await query.answer()


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
async def _handle_search_callback(
    meetup: Meetup,
    query: CallbackQuery,
    container: Container,
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    user_id: int,
) -> None:
    """Handle search button callback — send the substitutes message on demand."""
    if not settings.telegram.is_authorized(user_id):
        await query.answer(
            "Solo los administradores pueden realizar esta acción.", show_alert=True
        )
        return
    if not meetup.is_signup_open():
        await query.answer(
            "Los equipos ya están hechos, no se puede buscar más jugadores.", show_alert=True
        )
        return
    if not settings.telegram.substitutes.meetups:
        await query.answer("El chat de suplentes no está configurado.", show_alert=True)
        return
    try:
        await _do_search(meetup, container, bot, settings)
        await query.answer("Mensaje enviado a suplentes.")
    except Exception:  # pylint: disable=broad-except
        logger.exception("Unexpected error in search callback")
        await query.answer("Ha ocurrido un error inesperado.", show_alert=True)


def _parse_meetup_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _validate_player_id(player_id_str: str) -> PlayerId | None:
    try:
        return PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError:
        return None


def _process_action(
    action: str, meetup_date: datetime, player: "Player", container: Container
) -> bool:
    """Add or remove the player based on the action.

    Substring matching covers both the regular and substitute variants
    (``join``/``join_sub`` and ``leave``/``leave_sub``).
    """
    if "join" in action:
        try:
            container.add_player_to_meetup_by_id().execute(meetup_date, player.id)
            logger.info("Player '%s' joined meetup %s", player.name, meetup_date)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error processing join for player '%s'", player.name)
            return False
    if "leave" in action:
        try:
            container.remove_player_from_meetup_by_id().execute(meetup_date, player.id)
            logger.info("Player '%s' left meetup %s", player.name, meetup_date)
            return True
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unexpected error processing leave for player '%s'", player.name)
            return False
    return False
