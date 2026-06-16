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

COMMAND_DESCRIPTIONS: dict[str, str] = {
    "help": "Show this message",
    "player_new": "Create a new player",
    "player_rename": "Rename a player",
    "player_delete": "Delete a player",
    "player_list": "List all players",
    "player_change_group": "Change player group",
    "player_link": "Link Telegram ID to player",
    "player_unlink": "Unlink a player's Telegram ID",
    "meetup_new": "Create a new meetup",
    "meetup_next": "Create meetup for next default day",
    "meetup_list": "List all meetups",
    "meetup_show": "Show meetup details",
    "meetup_add_player": "Add player to meetup",
    "meetup_remove_player": "Remove player from meetup",
    "meetup_search": "Send substitutes message",
    "meetup_create_teams": "Create random teams",
    "meetup_lock": "Remove inline buttons from callup messages",
    "meetup_unlock": "Restore inline buttons on callup messages",
    "meetup_match_qr": "Send QR code with match URL",
    "meetup_stats": "Show statistics",
    "meetup_change_location": "Change meetup location",
    "meetup_change_date": "Change meetup date",
}

_MD_V2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def setup_general_handlers(application):
    """Register general handlers."""
    add_command(application, "help", help_handler)


def add_command(application, name, handler) -> None:
    """Register a handler under its canonical name and its short alias."""
    alias = short_alias(name)
    names = [name] if alias is None else [name, alias]
    application.add_handler(CommandHandler(names, handler))


def short_alias(name: str) -> str | None:
    """Return the abbreviated alias for a grouped command, or None."""
    for prefix, short in (("player_", "p_"), ("meetup_", "m_")):
        if name.startswith(prefix):
            return short + name[len(prefix) :]
    return None


async def register_bot_commands(bot) -> None:
    """Register the command menu with Telegram via set_my_commands."""
    await bot.set_my_commands(build_bot_commands())


def build_bot_commands() -> list[BotCommand]:
    """Build the BotCommand list from COMMAND_DESCRIPTIONS (canonical names only)."""
    return [BotCommand(name, desc) for name, desc in COMMAND_DESCRIPTIONS.items()]


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
    """Render the MarkdownV2 help text from COMMAND_DESCRIPTIONS."""
    lines = [r"*Available Commands:*"]
    current_category: str | None = None
    for name, desc in COMMAND_DESCRIPTIONS.items():
        category = _category(name)
        if category != current_category:
            lines.append("")
            lines.append(rf"*{category}:*")
            current_category = category
        lines.append(rf"`/{name}` \- {_escape_md(desc)}")
    return "\n".join(lines)


def _category(name: str) -> str:
    """Derive the help category from the command's group prefix."""
    if name.startswith("player_"):
        return "Player"
    if name.startswith("meetup_"):
        return "Meetup"
    return "General"


def _escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters in text."""
    return "".join(f"\\{ch}" if ch in _MD_V2_SPECIAL else ch for ch in text)
