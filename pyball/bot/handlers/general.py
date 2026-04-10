"""General command handlers."""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


def setup_general_handlers(application):
    """Register general handlers."""
    application.add_handler(CommandHandler("help", help_handler))


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    message = update.message
    if message is None:
        return

    text = """<b>Available Commands:</b>

<b>Player:</b>
/new_player - Create a new player
/rename_player - Rename a player
/delete_player - Delete a player
/list_players - List all players
/change_group - Change player group
/link_player - Link Telegram ID to player
/unlink_player - Unlink Telegram ID

<b>Meetup:</b>
/new_meetup - Create a new meetup
/next_meetup - Create meetup for next default day
/add_player - Add player to meetup
/remove_player - Remove player from meetup
/create_teams - Create balanced teams
/list_meetups - List all meetups
/show_meetup - Show meetup details

<b>Callup:</b>
/search - Send substitutes message"""
    await message.reply_text(text, parse_mode="HTML")
