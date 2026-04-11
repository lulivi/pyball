"""Inline button callback handler."""

import logging

from datetime import datetime
from typing import Final

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from pyball.application.container import Container
from pyball.bot.formatters import build_main_keyboard, format_main_message, parse_callback_data
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram_mapping import TelegramMappingStore
from pyball.settings import load_settings

logger = logging.getLogger(__name__)


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
    if action == "join":
        if player_id not in meetup.players:
            meetup.add_player(player_id)
            return True
        return False
    if action == "leave":
        try:
            meetup.remove_player(player_id)
            return True
        except Exception as error:
            logger.warning("Player not in meetup: %s", error)
            return False
    return False


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query

    if query is None or query.message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    settings = context.bot_data.get("settings")
    if settings is None:
        settings = load_settings()

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

    player_repo = container.player_repository
    player_names = {str(p.id.value): p.name for p in player_repo.find_all()}

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

    all_players = player_repo.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}

    text = format_main_message(meetup, player_names, player_groups)
    keyboard = build_main_keyboard(meetup.date)

    if modified:
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as error:
            logger.error("Failed to edit message: %s", error)
            await query.answer("Error updating message.", show_alert=True)
    else:
        if action == "join":
            await query.answer("Ya estás unido a este meetup.", show_alert=True)
        elif action == "leave":
            await query.answer("No estás en este meetup.", show_alert=True)


def create_callback_handler() -> CallbackQueryHandler:
    """Create the callback query handler."""
    return CallbackQueryHandler(callback_handler)
