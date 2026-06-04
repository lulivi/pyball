# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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

*General:*
`/help` \- Show this message

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
`/lock` \- Remove inline buttons from callup messages
`/unlock` \- Restore inline buttons on callup messages
`/match_qr` \- Send QR code with match URL
`/stats` \- Show statistics"""
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
