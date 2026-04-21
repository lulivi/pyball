"""General command handlers."""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from pyball.logger import log_func


def setup_general_handlers(application):
    """Register general handlers."""
    application.add_handler(CommandHandler("help", help_handler))


@log_func
async def help_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    message = update.message
    if message is None:
        return

    text = r"""*Available Commands:*

*Player:*
`/new_player` \- Create a new player
`/rename_player` \- Rename a player
`/delete_player` \- Delete a player
`/list_players` \- List all players
`/change_group` \- Change player group
`/link_player` \- Link Telegram ID to player
`/unlink_player` \- Unlink Telegram ID

*Meetup:*
`/new_meetup` \- Create a new meetup
`/next_meetup` \- Create meetup for next default day
`/list_meetups` \- List all meetups
`/show_meetup` \- Show meetup details
`/add_player` \- Add player to meetup
`/remove_player` \- Remove player from meetup
`/search` \- Send substitutes message
`/create_teams` \- Create random teams
`/start_match` \- Initialize match page"""
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
