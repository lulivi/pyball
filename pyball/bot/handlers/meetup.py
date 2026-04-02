"""Meetup command handlers."""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from pyball.application.container import Container
from pyball.application.meetup.add_player import REGULAR, SUBSTITUTE
from pyball.bot.auth import authorized
from pyball.domain.meetup.models import MeetupId

logger = logging.getLogger(__name__)


def setup_meetup_handlers(application):
    """Register meetup-related handlers."""
    application.add_handler(CommandHandler("new_meetup", new_meetup_handler))
    application.add_handler(CommandHandler("add_player", add_player_handler))
    application.add_handler(CommandHandler("remove_player", remove_player_handler))
    application.add_handler(CommandHandler("create_teams", create_teams_handler))
    application.add_handler(CommandHandler("list_meetups", list_meetups_handler))
    application.add_handler(CommandHandler("show_meetup", show_meetup_handler))


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
