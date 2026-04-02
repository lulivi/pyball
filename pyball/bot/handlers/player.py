"""Player command handlers."""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from pyball.application.player import CreatePlayer, RenamePlayer, DeletePlayer
from pyball.infrastructure import JsonPlayerRepository
from pyball.settings import load_settings


def setup_player_handlers(application):
    """Register player-related handlers."""
    application.add_handler(CommandHandler("new_player", new_player_handler))
    application.add_handler(CommandHandler("rename_player", rename_player_handler))
    application.add_handler(CommandHandler("delete_player", delete_player_handler))
    application.add_handler(CommandHandler("list_players", list_players_handler))


async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    create_player = CreatePlayer(player_repo)

    if not context.args:
        await update.message.reply_text("Usage: /new_player <name>")
        return

    name = " ".join(context.args)
    try:
        player = create_player.execute(name)
        await update.message.reply_text(f"Player '{player.name}' created!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rename_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    rename_player = RenamePlayer(player_repo)

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /rename_player <player_id> <new_name>")
        return

    player_id = context.args[0]
    new_name = " ".join(context.args[1:])
    try:
        player = rename_player.execute(player_id, new_name)
        await update.message.reply_text(f"Player renamed to '{player.name}'!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    delete_player = DeletePlayer(player_repo)

    if not context.args:
        await update.message.reply_text("Usage: /delete_player <player_id>")
        return

    player_id = context.args[0]
    try:
        delete_player.execute(player_id)
        await update.message.reply_text("Player deleted!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)

    players = player_repo.find_all()
    if not players:
        await update.message.reply_text("No players found.")
        return

    lines = ["*Players:*"]
    for p in players:
        lines.append(f"- {p.name} (id: {p.id.value})")

    await update.message.reply_text("\n".join(lines))
