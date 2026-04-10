"""Inline button callback handler."""

from datetime import datetime

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from pyball.application.container import Container
from pyball.bot.formatters import (
    build_main_keyboard,
    format_main_message,
    parse_callback_data,
)
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram_mapping import TelegramMappingStore
from pyball.settings import load_settings


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()

    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    settings = context.bot_data.get("settings")
    if not settings:
        settings = load_settings()

    mapping_store = TelegramMappingStore(settings.paths.mappings_file)

    parsed = parse_callback_data(query.data)
    if not parsed:
        await query.edit_message_text("Invalid callback data.")
        return

    action, date_str = parsed

    try:
        meetup_date = datetime.fromisoformat(date_str)
    except ValueError:
        await query.edit_message_text("Invalid date format.")
        return

    meetup_repo = container.meetup_repository

    meetup = None
    all_meetups = meetup_repo.find_all()
    for m in all_meetups:
        if m.date.date() == meetup_date.date():
            meetup = m
            break

    if not meetup:
        await query.edit_message_text("Meetup not found.")
        return

    player_repo = container.player_repository
    player_names = {p.id.value: p.name for p in player_repo.find_all()}

    telegram_id = query.from_user.id

    player_id_str = mapping_store.get_player_id(telegram_id)
    if not player_id_str:
        await query.edit_message_text(
            "No player linked to your Telegram account. Contact admin to register."
        )
        return

    try:
        player_id = PlayerId.from_string(player_id_str)
    except Exception:
        await query.edit_message_text("Invalid player mapping. Contact admin.")
        return

    if action == "join":
        meetup.add_player(player_id)
    elif action == "leave":
        try:
            meetup.remove_player(player_id)
        except Exception:
            pass

    meetup_repo.save(meetup)

    player_names = {p.id.value: p.name for p in player_repo.find_all()}

    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)
    await query.edit_message_text(text, reply_markup=keyboard)


def create_callback_handler() -> CallbackQueryHandler:
    """Create the callback query handler."""
    return CallbackQueryHandler(callback_handler)
