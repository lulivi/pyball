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
"""Meetup command handlers."""
from __future__ import annotations

import logging
from datetime import datetime

import telegram
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.application.meetup.compute_stats import ComputeStats
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.bot.auth import authorized
from pyball.infrastructure.telegram.bot.handlers.general import add_command
from pyball.infrastructure.telegram.bot.reactions import react_ok
from pyball.infrastructure.telegram.formatters import (
    build_main_keyboard,
    format_display,
    format_main_message,
    parse_display,
)
from pyball.infrastructure.telegram.message_store import MessageTracking
from pyball.infrastructure.telegram.notifications import send_substitutes_message
from pyball.infrastructure.telegram.settings import TelegramAppSettings, TelegramSettings
from pyball.logger import log_func

logger = logging.getLogger(__name__)


def setup_meetup_handlers(application):
    """Register meetup-related handlers."""
    add_command(application, "meetup_show", show_handler)
    add_command(application, "meetup_stats", stats_handler)


@log_func
@authorized
async def show_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meetup_show command - repost the current convocatoria to its chats."""
    message = update.message
    if message is None:
        return
    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]

    meetup = await _resolve_meetup(message, context.args, settings, container, "meetup_show")
    if meetup is None:
        return

    try:
        await _show_regulars_message(meetup, container, context.bot, settings)

        player_ids = set(meetup.players)
        has_substitutes = any(
            p.group == "substitute"
            for p in container.player_repository.find_all()
            if p.id in player_ids
        )
        if has_substitutes and settings.telegram.substitutes.meetups:
            await send_substitutes_message(context.bot, settings, container, meetup)

        await react_ok(context.bot, message)
    except telegram.error.TelegramError as error:
        logger.error("Telegram error showing meetup: %s", error)
        await message.reply_text("Error de Telegram al mostrar la convocatoria.")
    except Exception:
        logger.exception("Unexpected error showing meetup")
        await message.reply_text("Error al mostrar la convocatoria.")


@log_func
@authorized
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meetup_stats command — send a stats image for the requested scope."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or args[0] not in ("temporada", "historico"):
        await message.reply_text(
            text="Usa `/meetup_stats temporada` o `/meetup_stats historico`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    scope = "season" if args[0] == "temporada" else "alltime"
    container: Container = context.bot_data["container"]
    telegram_settings: TelegramSettings = context.bot_data["settings"].telegram

    message_thread_id: int | None = None
    if message.chat_id == telegram_settings.regulars.stats.chat_id:
        message_thread_id = telegram_settings.regulars.stats.message_thread_id

    caption = "📊 Esta temporada" if scope == "season" else "📊 Histórico"

    try:
        report = ComputeStats(
            container.meetup_repository,
            container.player_repository,
            container.legacy_stats,
        ).execute()
        png = await StatsHtmlRenderer().render(report, scope=scope)
        await context.bot.send_photo(
            chat_id=message.chat_id,
            message_thread_id=message_thread_id,
            photo=png,
            caption=caption,
        )
        await react_ok(context.bot, message)
    except Exception:
        logger.exception("Unexpected error sending stats")
        await message.reply_text("Error al generar las estadísticas.")


async def _show_regulars_message(
    meetup: Meetup,
    container: Container,
    bot: telegram.Bot,
    settings: TelegramAppSettings,
) -> None:
    """Send a fresh regulars callup message to the regulars chat and (re)track it."""
    player_names = _get_player_names(container.player_repository)
    text = format_main_message(
        meetup,
        player_names,
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
        legacy_stats=container.legacy_stats,
    )
    keyboard = build_main_keyboard(meetup.date) if meetup.is_signup_open() else None
    meetups = settings.telegram.regulars.meetups

    msg = await bot.send_message(
        chat_id=meetups.chat_id,
        text=text,
        reply_markup=keyboard,
        message_thread_id=meetups.message_thread_id,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    store.save_message(
        meetup.date,
        "regular",
        MessageTracking(
            chat_id=meetups.chat_id,
            thread_id=meetups.message_thread_id,
            message_id=msg.message_id,
        ),
    )


async def _resolve_meetup(
    message: Message,
    args: list[str] | None,
    settings: TelegramAppSettings,
    container: Container,
    command: str = "",
) -> Meetup | None:
    """Return meetup for given date args, or the most recent active meetup."""
    if args and len(args) >= 2:
        date_str = f"{args[0]} {args[1]}"
        try:
            meetup_date = parse_display(date_str, settings.pyball.display_date_format)
        except ValueError:
            await message.reply_text(
                _date_usage_msg(command, settings.pyball.display_date_format),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return None
        meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return None
        return meetup
    try:
        return container.get_active_meetup().execute()
    except MeetupNotFoundError:
        await message.reply_text("No hay ningún partido activo.")
        return None


def _date_usage_msg(cmd: str, fmt: str, suffix: str = "") -> str:
    """Build a MarkdownV2-escaped date-format help message for bot commands."""
    example = format_display(datetime.now(), fmt)
    suffix_part = rf" {suffix}" if suffix else ""
    return (
        r"Formato de fecha no válido\."
        "\n"
        rf"Formato: `{fmt}`"
        "\n"
        rf"Ejemplo: `/{cmd}` `{example}`{suffix_part}"
    )


def _get_player_names(player_repo) -> dict:
    """Build a {str_uuid: name} lookup dict for all players."""
    all_players = player_repo.find_all()
    return {str(p.id.value): p.name for p in all_players}
