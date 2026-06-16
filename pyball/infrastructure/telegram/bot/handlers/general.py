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

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from pyball.logger import log_func

COMMAND_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "help": ("Show this message", "General"),
    "new_player": ("Create a new player", "Player"),
    "rename_player": ("Rename a player", "Player"),
    "delete_player": ("Delete a player", "Player"),
    "list_players": ("List all players", "Player"),
    "change_group": ("Change player group", "Player"),
    "link_player": ("Link Telegram ID to player", "Player"),
    "unlink_player": ("Unlink a player's Telegram ID", "Player"),
    "new_meetup": ("Create a new meetup", "Meetup"),
    "next_meetup": ("Create meetup for next default day", "Meetup"),
    "list_meetups": ("List all meetups", "Meetup"),
    "show_meetup": ("Show meetup details", "Meetup"),
    "add_player": ("Add player to meetup", "Meetup"),
    "remove_player": ("Remove player from meetup", "Meetup"),
    "search": ("Send substitutes message", "Meetup"),
    "create_teams": ("Create random teams", "Meetup"),
    "lock": ("Remove inline buttons from callup messages", "Meetup"),
    "unlock": ("Restore inline buttons on callup messages", "Meetup"),
    "match_qr": ("Send QR code with match URL", "Meetup"),
    "stats": ("Show statistics", "Meetup"),
    "change_location": ("Change meetup location", "Meetup"),
    "change_date": ("Change meetup date", "Meetup"),
}

_MD_V2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def setup_general_handlers(application):
    """Register general handlers."""
    application.add_handler(CommandHandler("help", help_handler))


async def register_bot_commands(bot) -> None:
    """Register the command menu with Telegram via set_my_commands."""
    await bot.set_my_commands(build_bot_commands())


def build_bot_commands() -> list[BotCommand]:
    """Build the BotCommand list from COMMAND_DESCRIPTIONS."""
    return [BotCommand(name, desc) for name, (desc, _category) in COMMAND_DESCRIPTIONS.items()]


def registered_commands(application) -> set[str]:
    """Collect every command name from the application's registered CommandHandlers."""
    names: set[str] = set()
    for group in application.handlers.values():
        for handler in group:
            if isinstance(handler, CommandHandler):
                names.update(handler.commands)
    return names


@log_func
async def help_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    message = update.message
    if message is None:
        return
    await message.reply_text(_render_help(), parse_mode=ParseMode.MARKDOWN_V2)


def _render_help() -> str:
    lines = [r"*Available Commands:*"]
    current_category: str | None = None
    for name, (desc, category) in COMMAND_DESCRIPTIONS.items():
        if category != current_category:
            lines.append("")
            lines.append(rf"*{category}:*")
            current_category = category
        lines.append(rf"`/{name}` \- {_escape_md(desc)}")
    return "\n".join(lines)


def _escape_md(text: str) -> str:
    return "".join(f"\\{ch}" if ch in _MD_V2_SPECIAL else ch for ch in text)
