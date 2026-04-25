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

from telegram import Update
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.bot.formatters import parse_callback_data
from pyball.bot.handlers.meetup import refresh_callup_messages
from pyball.domain.meetup.errors import PlayerNotInMeetupError
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.logger import log_func

logger = logging.getLogger(__name__)


@log_func
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query

    if query is None or query.message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.bot_mappings_file)

    callback_data = query.data
    if callback_data is None:
        await query.answer("Invalid callback data.", show_alert=True)
        return

    parsed = parse_callback_data(callback_data)
    if not parsed:
        await query.answer("Invalid callback data.", show_alert=True)
        return

    action, date_str = parsed

    meetup_date = _parse_meetup_date(date_str)
    if meetup_date is None:
        await query.answer("Invalid date format.", show_alert=True)
        return

    meetup_repo = container.meetup_repository

    meetup = _find_meetup(meetup_repo, meetup_date)

    if not meetup:
        await query.answer("Meetup not found.", show_alert=True)
        return

    from_user = query.from_user
    if from_user is None:
        await query.answer("Invalid user.", show_alert=True)
        return
    telegram_id = from_user.id

    player_id_str = _get_player_id(telegram_id, mapping_store)
    if not player_id_str:
        await query.answer(
            "No player linked to your Telegram account. Contact admin to register.",
            show_alert=True,
        )
        return

    player_id = _validate_player_id(player_id_str)
    if not player_id:
        await query.answer("Invalid player mapping. Contact admin.", show_alert=True)
        return

    modified = _process_action(action, meetup, player_id)

    if modified:
        meetup_repo.save(meetup)
        await refresh_callup_messages(context.bot, settings, container, meetup)
        await query.answer()
    else:
        if action == "join":
            await query.answer("Ya estás unido a este meetup.", show_alert=True)
        elif action == "leave":
            await query.answer("No estás en este meetup.", show_alert=True)


def _parse_meetup_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _find_meetup(meetup_repo, date: datetime) -> Meetup | None:
    all_meetups = meetup_repo.find_all()
    for m in all_meetups:
        if m.date.date() == date.date():
            return m
    return None


def _get_player_id(telegram_id: int, mapping_store: TelegramMappingStore) -> str | None:
    return mapping_store.get_player_id(telegram_id)


def _validate_player_id(player_id_str: str) -> PlayerId | None:
    try:
        return PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError:
        return None


def _process_action(action: str, meetup: Meetup, player_id: PlayerId) -> bool:
    if "join" in action:
        if player_id not in meetup.players:
            meetup.add_player(player_id)
            return True
        return False
    if "leave" in action:
        try:
            meetup.remove_player(player_id)
            return True
        except PlayerNotInMeetupError as error:
            logger.warning("Player not in meetup: %s", error)
            return False
    return False
