"""Meetup command handlers."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from pyball.application.container import Container
from pyball.application.meetup.add_player import REGULAR, SUBSTITUTE
from pyball.bot.auth import authorized
from pyball.bot.formatters import format_main_message, format_subs_message, build_main_keyboard, build_subs_keyboard
from pyball.domain.meetup.models import MeetupId
from pyball.infrastructure import TelegramMessageStore
from pyball.infrastructure.telegram_store import MessageTracking
from pyball.settings import load_settings

logger = logging.getLogger(__name__)


def setup_meetup_handlers(application):
    """Register meetup-related handlers."""
    application.add_handler(CommandHandler("new_meetup", new_meetup_handler))
    application.add_handler(CommandHandler("add_player", add_player_handler))
    application.add_handler(CommandHandler("remove_player", remove_player_handler))
    application.add_handler(CommandHandler("create_teams", create_teams_handler))
    application.add_handler(CommandHandler("list_meetups", list_meetups_handler))
    application.add_handler(CommandHandler("show_meetup", show_meetup_handler))
    application.add_handler(CommandHandler("callup", callup_handler))
    application.add_handler(CommandHandler("search", search_handler))


def _get_player_names(player_ids, player_repo) -> dict:
    """Build a player name lookup dict, fetching all players at once."""
    all_players = player_repo.find_all()
    return {p.id: p.name for p in all_players}


@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_meetup command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    if not context.args:
        await update.message.reply_text("Usage: /new_meetup YYYY-MM-DD HH:MM")
        return

    try:
        date_str = " ".join(context.args)
        date = datetime.fromisoformat(date_str)
    except ValueError:
        await update.message.reply_text("Invalid date format. Use: /new_meetup YYYY-MM-DD HH:MM")
        return

    try:
        meetup = container.create_meetup().execute(date)
        await update.message.reply_text(
            f"Meetup created for {date.strftime('%Y-%m-%d %H:%M')}!"
        )
    except Exception as e:
        logger.exception("Error creating meetup")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_player command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /add_player <meetup_id> <player_id> [regular|substitute]"
        )
        return

    meetup_id = context.args[0]
    player_id = context.args[1]
    role = context.args[2] if len(context.args) > 2 else REGULAR

    if role not in (REGULAR, SUBSTITUTE):
        role = REGULAR

    try:
        container.add_player_to_meetup().execute(meetup_id, player_id, role)
        await update.message.reply_text(f"Player added as {role}!")
    except Exception as e:
        logger.exception("Error adding player to meetup")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove_player command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /remove_player <meetup_id> <player_id>")
        return

    meetup_id = context.args[0]
    player_id = context.args[1]

    try:
        container.remove_player_from_meetup().execute(meetup_id, player_id)
        await update.message.reply_text("Player removed from meetup!")
    except Exception as e:
        logger.exception("Error removing player from meetup")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_teams command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    if not context.args:
        await update.message.reply_text("Usage: /create_teams <meetup_id>")
        return

    meetup_id = context.args[0]

    try:
        meetup = container.create_teams().execute(meetup_id)

        if not meetup.teams:
            await update.message.reply_text("No teams created.")
            return

        player_names = _get_player_names(None, container.player_repository)
        lines = ["*Teams:*"]
        for team in meetup.teams:
            lines.append(f"\n{team.name}:")
            for player_id in team.players:
                name = player_names.get(player_id, str(player_id.value))
                lines.append(f"  - {name}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.exception("Error creating teams")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def list_meetups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_meetups command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    meetups = container.meetup_repository.find_all()

    if not meetups:
        await update.message.reply_text("No meetups found.")
        return

    lines = ["*Meetups:*"]
    for m in meetups:
        lines.append(f"- {m.date.strftime('%Y-%m-%d %H:%M')} (id: {m.id.value})")

    await update.message.reply_text("\n".join(lines))


@authorized
async def show_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /show_meetup command."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()

    if not context.args:
        await update.message.reply_text("Usage: /show_meetup <meetup_id>")
        return

    meetup_id = context.args[0]

    try:
        meetup = container.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))

        if not meetup:
            await update.message.reply_text("Meetup not found.")
            return

        player_names = _get_player_names(None, container.player_repository)
        lines = [f"*Meetup: {meetup.date.strftime('%Y-%m-%d %H:%M')}*"]

        if meetup.regulars:
            lines.append("\n*Regulars:*")
            for player_id in meetup.regulars:
                name = player_names.get(player_id, str(player_id.value))
                lines.append(f"  - {name}")

        if meetup.substitutes:
            lines.append("\n*Substitutes:*")
            for player_id in meetup.substitutes:
                name = player_names.get(player_id, str(player_id.value))
                lines.append(f"  - {name}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        logger.exception("Error showing meetup")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def callup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /callup command - create meetup and send main message."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()
    
    settings = load_settings()
    
    if not context.args:
        await update.message.reply_text("Usage: /callup YYYY-MM-DD HH:MM [location]")
        return
    
    date_str = " ".join(context.args[:-1]) if len(context.args) > 2 else context.args[0]
    time_str = context.args[1] if len(context.args) > 1 else "20:00"
    location = context.args[2] if len(context.args) > 2 else "Park"
    
    try:
        full_date_str = f"{date_str} {time_str}"
        meetup_date = datetime.fromisoformat(full_date_str)
    except ValueError:
        await update.message.reply_text("Invalid date. Use: /callup YYYY-MM-DD HH:MM [location]")
        return
    
    if not settings.telegram.regulars.chat_id:
        await update.message.reply_text("Regulars chat not configured.")
        return
    
    try:
        meetup = container.create_meetup().execute(meetup_date)
        meetup.location = location
        container.meetup_repository.save(meetup)
    except Exception as e:
        logger.exception("Error creating meetup")
        await update.message.reply_text("An error occurred. Please try again.")
        return
    
    player_names = {p.id: p.name for p in container.player_repository.find_all()}
    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)
    
    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.regulars.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.regulars.thread_id or None,
        )
        
        store = TelegramMessageStore(settings.paths.mappings_file.parent / "messages.json")
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "main",
            MessageTracking(
                chat_id=settings.telegram.regulars.chat_id,
                thread_id=settings.telegram.regulars.thread_id or None,
                message_id=msg.message_id,
            ),
        )
        
        await update.message.reply_text(f"Callup created! Message sent.")
    except Exception as e:
        logger.exception("Error sending callup message")
        await update.message.reply_text("Meetup created but failed to send message.")


@authorized
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command - send substitutes message."""
    container: Container = context.bot_data.get('container')
    settings = load_settings()
    
    if not context.args:
        await update.message.reply_text("Usage: /search YYYY-MM-DD")
        return
    
    date_str = context.args[0]
    
    try:
        meetup_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Invalid date. Use: /search YYYY-MM-DD")
        return
    
    from pyball.domain.meetup.repository import MeetupRepository
    meetup = None
    for m in container.meetup_repository.find_all():
        if m.date.date() == meetup_date.date():
            meetup = m
            break
    
    if not meetup:
        await update.message.reply_text("Meetup not found.")
        return
    
    if not settings.telegram.substitutes.chat_id:
        await update.message.reply_text("Substitutes chat not configured.")
        return
    
    player_names = {p.id: p.name for p in container.player_repository.find_all()}
    text = format_subs_message(meetup, player_names)
    keyboard = build_subs_keyboard(meetup.date)
    
    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.substitutes.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.substitutes.thread_id or None,
        )
        
        store = TelegramMessageStore(settings.paths.mappings_file.parent / "messages.json")
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "subs",
            MessageTracking(
                chat_id=settings.telegram.substitutes.chat_id,
                thread_id=settings.telegram.substitutes.thread_id or None,
                message_id=msg.message_id,
            ),
        )
        
        await update.message.reply_text("Substitutes message sent!")
    except Exception as e:
        logger.exception("Error sending substitutes message")
        await update.message.reply_text("Failed to send message.")
