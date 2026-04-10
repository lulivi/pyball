"""Player command handlers."""

import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.bot.auth import authorized
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)

logger = logging.getLogger(__name__)


def setup_player_handlers(application):
    """Register player-related handlers."""
    application.add_handler(CommandHandler("new_player", new_player_handler))
    application.add_handler(CommandHandler("rename_player", rename_player_handler))
    application.add_handler(CommandHandler("delete_player", delete_player_handler))
    application.add_handler(CommandHandler("list_players", list_players_handler))
    application.add_handler(CommandHandler("change_group", change_group_handler))
    application.add_handler(CommandHandler("help", help_handler))


@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_player command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /new_player <name> <regular|substitute>")
        return

    name = context.args[0]
    group = context.args[1]

    if group not in ("regular", "substitute"):
        await update.message.reply_text("Group must be 'regular' or 'substitute'")
        return

    try:
        player = container.create_player().execute(name, group)
        await update.message.reply_text(f"Player '{player.name}' created as {group}!")
    except PlayerAlreadyExistsError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.exception("Error creating player")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rename_player command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /rename_player <player_id> <new_name>")
        return

    player_id = context.args[0]
    new_name = " ".join(context.args[1:])
    try:
        player = container.rename_player().execute(player_id, new_name)
        await update.message.reply_text(f"Player renamed to '{player.name}'!")
    except InvalidPlayerIdError:
        await update.message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await update.message.reply_text("Player not found.")
    except NameAlreadyTakenError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.exception("Error renaming player")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    if not context.args:
        await update.message.reply_text("Usage: /delete_player <player_id>")
        return

    player_id = context.args[0]
    try:
        container.delete_player().execute(player_id)
        await update.message.reply_text("Player deleted!")
    except InvalidPlayerIdError:
        await update.message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await update.message.reply_text("Player not found.")
    except Exception as e:
        logger.exception("Error deleting player")
        await update.message.reply_text("An error occurred. Please try again.")


@authorized
async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    players = container.player_repository.find_all()
    if not players:
        await update.message.reply_text("No players found.")
        return

    lines = ["*Players:*"]
    for p in players:
        lines.append(f"- {p.name} (id: {p.id.value})")

    await update.message.reply_text("\n".join(lines))


@authorized
async def change_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_group command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /change_group <player_name> <regular|substitute>")
        return

    player_name = context.args[0]
    new_group = context.args[1]

    if new_group not in ("regular", "substitute"):
        await update.message.reply_text("Group must be 'regular' or 'substitute'")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    try:
        use_case = container.change_player_group()
        player = use_case.execute(match.player_id, new_group)
        await update.message.reply_text(f"Player {player.name} changed to {new_group}!")
    except Exception as e:
        logger.exception("Error changing player group")
        await update.message.reply_text("Error changing player group.")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    text = """*Available Commands:*

*Player:*
/new_player <name> <regular|substitute> - Create a new player
/rename_player <player> <new_name> - Rename a player
/delete_player <player> - Delete a player
/list_players - List all players
/change_group <player> <regular|substitute> - Change player group

*Meetup:*
/new_meetup <YYYY-MM-DD HH:MM> - Create a new meetup
/add_player <YYYY-MM-DD HH:MM> <player> - Add player to meetup
/remove_player <YYYY-MM-DD HH:MM> <player> - Remove player from meetup
/create_teams <YYYY-MM-DD HH:MM> - Create balanced teams
/list_meetups - List all meetups
/show_meetup <YYYY-MM-DD HH:MM> - Show meetup details

*Callup:*
/callup [YYYY-MM-DD] [HH:MM] [location] - Create callup message
/search <YYYY-MM-DD> - Send substitutes message"""
    await update.message.reply_text(text, parse_mode="MarkdownV2")
