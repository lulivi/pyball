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


@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_player command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text("Usage: /new_player <name> <regular|substitute>")
        return

    name = args[0]
    group = args[1]

    if group not in ("regular", "substitute"):
        await message.reply_text("Group must be 'regular' or 'substitute'")
        return

    try:
        player = container.create_player().execute(name, group)
        await message.reply_text(f"Player '{player.name}' created as {group}!")
    except PlayerAlreadyExistsError as error:
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error creating player: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rename_player command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text("Usage: /rename_player <player_id> <new_name>")
        return

    player_id = args[0]
    new_name = " ".join(args[1:])
    try:
        player = container.rename_player().execute(player_id, new_name)
        await message.reply_text(f"Player renamed to '{player.name}'!")
    except InvalidPlayerIdError:
        await message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await message.reply_text("Player not found.")
    except NameAlreadyTakenError as error:
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error renaming player: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or not args:
        await message.reply_text("Usage: /delete_player <player_id>")
        return

    player_id = args[0]
    try:
        container.delete_player().execute(player_id)
        await message.reply_text("Player deleted!")
    except InvalidPlayerIdError:
        await message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await message.reply_text("Player not found.")
    except Exception as error:
        logger.exception("Error deleting player: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    players = container.player_repository.find_all()
    if not players:
        await message.reply_text("No players found.")
        return

    lines = ["*Players:*"]
    for p in players:
        lines.append(f"- {p.name} (id: {p.id.value})")

    await message.reply_text("\n".join(lines))


@authorized
async def change_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_group command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text("Usage: /change_group <player_name> <regular|substitute>")
        return

    player_name = args[0]
    new_group = args[1]

    if new_group not in ("regular", "substitute"):
        await message.reply_text("Group must be 'regular' or 'substitute'")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError as error:
        await message.reply_text(str(error))
        return

    try:
        use_case = container.change_player_group()
        player = use_case.execute(str(match.player_id.value), new_group)
        await message.reply_text(f"Player {player.name} changed to {new_group}!")
    except Exception as error:
        logger.exception("Error changing player group: %s", error)
        await message.reply_text("Error changing player group.")
