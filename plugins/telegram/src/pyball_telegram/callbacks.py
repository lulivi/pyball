"""The join/leave buttons of the callups.

A press joins or leaves through the plugin API; the event PyBall records for it then
refreshes the callups, like any other change.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from pyball_client import ApiError
from telegram import CallbackQuery, Update
from telegram.ext import ContextTypes

from pyball_telegram.api import JOIN, LEAVE, MEETUPS, PLAYERS, Meetup
from pyball_telegram.callups import Callups
from pyball_telegram.formatters import parse_callback_data
from pyball_telegram.state import LinkStore

logger = logging.getLogger(__name__)


async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Join or leave the meetup of the pressed button, as the player linked to the user."""
    query = update.callback_query
    if query is None or query.message is None:
        return
    parsed = parse_callback_data(query.data or "")
    if parsed is None:
        await query.answer("Datos de acción no válidos.", show_alert=True)
        return
    action, raw_date = parsed
    try:
        date = datetime.fromisoformat(raw_date)
    except ValueError:
        await query.answer("Formato de fecha no válido.", show_alert=True)
        return
    callups: Callups = context.bot_data["callups"]
    found = await callups.api.call(MEETUPS, params={"date": date.isoformat()})
    if not found:
        await query.answer("No se ha encontrado el meetup.", show_alert=True)
        return
    await _join_or_leave(action, found[0], query, callups)


async def _join_or_leave(  # pylint: disable=too-many-return-statements
    action: str, meetup: Meetup, query: CallbackQuery, callups: Callups
) -> None:
    """Apply ``action`` (join, leave, join_sub or leave_sub), or say why it cannot be."""
    if not meetup.signup_open():
        await query.answer(
            "Los equipos ya están hechos, no se puede apuntar ni salir del meetup.",
            show_alert=True,
        )
        return
    player_id = LinkStore(callups.config.mapping_file).player_id(query.from_user.id)
    if not player_id:
        await query.answer(
            "No tienes ningún jugador vinculado. Contacta con el administrador para registrarte.",
            show_alert=True,
        )
        return
    if not _is_uuid(player_id):
        await query.answer(
            "Vinculación de jugador no válida. Contacta con el administrador.", show_alert=True
        )
        return
    if not any(p.id == player_id for p in await callups.api.call(PLAYERS)):
        await query.answer(
            "Jugador no encontrado. Contacta con el administrador.", show_alert=True
        )
        return

    joining = action.startswith("join")
    if joining and player_id in meetup.players:
        await query.answer("Ya estás unido a este meetup.", show_alert=True)
        return
    if not joining and player_id not in meetup.players:
        await query.answer("No estás en este meetup.", show_alert=True)
        return
    if action == "join_sub" and not meetup.substitute_search:
        await query.answer("La búsqueda de suplentes está cerrada.", show_alert=True)
        return

    try:
        await callups.api.call(
            JOIN if joining else LEAVE, meetup_id=meetup.id, player_id=player_id
        )
    except ApiError:
        logger.exception("Could not %s player %s", action, player_id)
        return
    await query.answer()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
