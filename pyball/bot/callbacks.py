"""Inline button callback handler."""

import logging

from datetime import datetime

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from pyball.application.container import Container
from pyball.bot.formatters import build_main_keyboard, format_main_message, parse_callback_data
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram_mapping import TelegramMappingStore
from pyball.settings import load_settings

logger = logging.getLogger(__name__)


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

    mapping_store = TelegramMappingStore(settings.paths.mappings_file)

    callback_data = query.data
    if callback_data is None:
        await query.answer("Invalid callback data.", show_alert=True)
        return

    parsed = parse_callback_data(callback_data)
    if not parsed:
        await query.answer("Invalid callback data.", show_alert=True)
        return

    action, date_str = parsed

    try:
        meetup_date = datetime.fromisoformat(date_str)
    except ValueError:
        await query.answer("Invalid date format.", show_alert=True)
        return

    meetup_repo = container.meetup_repository

    meetup = None
    all_meetups = meetup_repo.find_all()
    for m in all_meetups:
        if m.date.date() == meetup_date.date():
            meetup = m
            break

    if not meetup:
        await query.answer("Meetup not found.", show_alert=True)
        return

    player_repo = container.player_repository
    player_names = {p.id.value: p.name for p in player_repo.find_all()}

    from_user = query.from_user
    if from_user is None:
        await query.answer("Invalid user.", show_alert=True)
        return
    telegram_id = from_user.id

    player_id_str = mapping_store.get_player_id(telegram_id)
    if not player_id_str:
        await query.answer(
            "No player linked to your Telegram account. Contact admin to register.",
            show_alert=True,
        )
        return

    try:
        player_id = PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError:
        await query.answer("Invalid player mapping. Contact admin.", show_alert=True)
        return

    if action == "join":
        meetup.add_player(player_id)
    elif action == "leave":
        try:
            meetup.remove_player(player_id)
        except Exception as error:
            logger.warning("Player not in meetup: %s", error)

    meetup_repo.save(meetup)

    player_names = {p.id.value: p.name for p in player_repo.find_all()}

    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)
    await query.edit_message_text(text, reply_markup=keyboard)


def create_callback_handler() -> CallbackQueryHandler:
    """Create the callback query handler."""
    return CallbackQueryHandler(callback_handler)
