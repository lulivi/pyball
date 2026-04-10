"""General command handlers."""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


def setup_general_handlers(application):
    """Register general handlers."""
    application.add_handler(CommandHandler("help", help_handler))


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