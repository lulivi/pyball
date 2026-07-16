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
"""Player command handlers."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.infrastructure.telegram.bot.auth import authorized
from pyball.infrastructure.telegram.bot.handlers.general import add_command
from pyball.infrastructure.telegram.bot.reactions import react_ok
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.logger import log_func

logger = logging.getLogger(__name__)


def setup_player_handlers(application):
    """Register player-related handlers."""
    add_command(application, "player_link", link_player_handler)
    add_command(application, "player_unlink", unlink_player_handler)


@log_func
@authorized
async def link_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_link command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")

    player_name, _, telegram_id_str = " ".join(context.args or []).partition(",")
    player_name = player_name.strip()
    telegram_id_str = telegram_id_str.strip()
    if not player_name or not telegram_id_str:
        await message.reply_text(
            text=r"Usage: `/player_link` `<player_name>, <telegram_id>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    try:
        telegram_id = int(telegram_id_str)
    except ValueError:
        await message.reply_text("ID de Telegram no válido. Debe ser un número.")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    player_id_str = str(match.player_id.value)

    existing_telegram_id = mapping_store.get_player_id(telegram_id)
    if existing_telegram_id:
        if existing_telegram_id == player_id_str:
            await message.reply_text("Este ID de Telegram ya está vinculado a este jugador.")
        else:
            await message.reply_text(
                "Este ID de Telegram ya está vinculado a otro jugador. "
                "Elimina el enlace primero con /player_unlink <player_name>"
            )
        return

    mapping_store.set_player_id(telegram_id, player_id_str)

    await react_ok(context.bot, message)


@log_func
@authorized
async def unlink_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_unlink command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")

    player_name = " ".join(context.args or []).strip()
    if not player_name:
        await message.reply_text(
            text=r"Usage: `/player_unlink` `<player_name>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_repo = container.player_repository
    try:
        match = fuzzy_match_player(player_name, player_repo.find_all())
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    telegram_id = mapping_store.get_telegram_id(str(match.player_id.value))
    if telegram_id is None:
        await message.reply_text("Este jugador no está vinculado a ningún ID de Telegram.")
        return

    mapping_store.delete_player_id(telegram_id)
    await react_ok(context.bot, message)
