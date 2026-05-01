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

import logging
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
import telegram
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.meetup.compute_stats import ComputeStats
from pyball.application.meetup.create_meetup import DuplicateMeetupError
from pyball.application.meetup.create_teams import InvalidMeetupDateError
from pyball.bot.auth import authorized
from pyball.exceptions import MeetupError
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.formatters import (
    build_main_keyboard,
    build_subs_keyboard,
    format_main_message,
    format_subs_message,
)
from pyball.infrastructure.telegram.message_store import MessageTracking
from pyball.infrastructure.telegram.notifications import refresh_callup_messages
from pyball.logger import log_func
from pyball.settings import CoreSettings, Settings, TelegramSettings

logger = logging.getLogger(__name__)


def generate_qr_bytes(url: str) -> BytesIO:
    """Generate a PNG QR code for url and return it as a seeked BytesIO buffer."""
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf


def setup_meetup_handlers(application):
    """Register meetup-related handlers."""
    application.add_handler(CommandHandler("new_meetup", new_meetup_handler))
    application.add_handler(CommandHandler("next_meetup", next_meetup_handler))
    application.add_handler(CommandHandler("add_player", add_player_handler))
    application.add_handler(CommandHandler("remove_player", remove_player_handler))
    application.add_handler(CommandHandler("create_teams", create_teams_handler))
    application.add_handler(CommandHandler("list_meetups", list_meetups_handler))
    application.add_handler(CommandHandler("show_meetup", show_meetup_handler))
    application.add_handler(CommandHandler("search", search_handler))
    application.add_handler(CommandHandler("start_match", start_match_handler))
    application.add_handler(CommandHandler("stats", stats_handler))


@log_func
@authorized
async def start_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start_match command — generate match URL and reply to admins only."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            text="Usage: `/start_match` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    date_str = f"{args[0]} {args[1]}"
    container: Container = context.bot_data["container"]
    telegram_settings: TelegramSettings = context.bot_data["settings"].telegram

    try:
        url = container.start_match().execute(date_str)
        qr = generate_qr_bytes(url)
        for admin in telegram_settings.admins_ids:
            try:
                qr.seek(0)
                await context.bot.send_photo(
                    chat_id=admin,
                    photo=qr,
                    caption=f"🔗 Enlace del partido:\n{url}",
                )
            except telegram.error.Forbidden:
                logger.error("Could not send message to '%s' admin", admin)

    except ValueError as error:
        await message.reply_text(str(error))
    except MeetupError as error:
        logger.error("Meetup error starting match: %s", error)
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error starting match: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@log_func
@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_meetup command - creates meetup and sends callup messages."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            text="Usage: `/new_meetup` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        date = datetime.strptime(f"{args[0]} {args[1]}", "%Y/%m/%d %H:%M")
    except ValueError:
        await message.reply_text(
            r"Invalid date format\. Use: `/new_meetup` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await _create_meetup_and_send(date, update, context)


@log_func
@authorized
async def next_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /next_meetup command - creates meetup for next default weekday and sends callup."""
    message = update.message
    if message is None:
        return

    settings = context.bot_data["settings"]
    next_date = _get_next_weekday(settings.pyball)
    day_name = next_date.strftime("%A")
    await message.reply_text(
        text=rf"Creating meetup for `{next_date.strftime('%Y/%m/%d %H:%M')}` \({day_name}\)\.\.\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    await _create_meetup_and_send(next_date, update, context)


async def _create_meetup_and_send(
    date: datetime, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create meetup and send callup messages. Shared by new_meetup and next_meetup."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings: Settings = context.bot_data["settings"]

    try:
        meetup = container.create_meetup().execute(date, settings.pyball.location)
    except DuplicateMeetupError:
        await message.reply_text(
            text=rf"Meetup already exists at `{date.strftime('%Y/%m/%d %H:%M')}`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    except InvalidMeetupDateError as error:
        await message.reply_text(str(error))
        return
    except MeetupError as error:
        logger.error("Error creating meetup (domain): %s", error)
        await message.reply_text("Meetup error. Please try again.")
        return
    except telegram.error.TelegramError as error:
        logger.error("Error creating meetup (Telegram): %s", error)
        await message.reply_text("Telegram error. Please try again.")
        return
    except Exception as error:
        logger.exception("Error creating meetup: %s", error)
        await message.reply_text("An error occurred. Please try again.")
        return

    await _send_callup_messages(context, settings, container, meetup)
    await message.reply_text(
        text=rf"Meetup `{date.strftime('%Y/%m/%d %H:%M')}` created and callup sent\!",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def _send_callup_messages(context, settings, container, meetup) -> None:
    """Send callup messages to regulars and substitutes chats."""
    player_repo = container.player_repository
    all_players = player_repo.find_all()
    player_names = {str(player.id.value): player.name for player in all_players}

    text = format_main_message(
        meetup, player_names, team_display_names=settings.pyball.team_display_names
    )
    keyboard = build_main_keyboard(meetup.date)

    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.regulars.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.regulars.meetups_thread_id or None,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        store = TelegramMessageStore(settings.paths.bot_messages_file)
        store.save_message(
            meetup.date,
            "regular",
            MessageTracking(
                chat_id=settings.telegram.regulars.chat_id,
                thread_id=settings.telegram.regulars.meetups_thread_id or None,
                message_id=msg.message_id,
            ),
        )
    except telegram.error.TelegramError as error:
        logger.error("Error sending regulars message (Telegram): %s", error)
    except Exception as error:
        logger.exception("Error sending regulars message: %s", error)


def _get_next_weekday(pyball_settings: CoreSettings) -> datetime:
    """Calculate next occurrence of default weekday."""
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    target_weekday = day_map.get(pyball_settings.default_week_day.lower(), 2)

    today = datetime.now()
    days_until_target = (target_weekday - today.weekday() + 7) % 7

    if days_until_target == 0:
        days_until_target = 7

    next_date = today + timedelta(days=days_until_target)
    hour, minute = map(int, pyball_settings.default_hour.split(":"))
    return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


@log_func
@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 3:
        await message.reply_text(
            r"Usage: `/add_player` `YYYY/MM/DD HH:MM` `<name1>`, `<name2>`, \.\.\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    date_str = f"{args[0]} {args[1]}"
    names = [n.strip() for n in " ".join(args[2:]).split(",") if n.strip()]

    if not names:
        await message.reply_text(
            r"Usage: `/add_player` `YYYY/MM/DD HH:MM` `<name1>`, `<name2>`, \.\.\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    settings = context.bot_data["settings"]
    added, failed = [], []
    meetup = None
    use_case = container.add_player_to_meetup()

    for name in names:
        try:
            meetup = use_case.execute(date_str, name)
            added.append(name)
        except ValueError as error:
            failed.append(f"{name}: {error}")
        except MeetupError as error:
            logger.error("Meetup error adding %s: %s", name, error)
            failed.append(f"{name}: meetup error")
        except Exception as error:
            logger.exception("Error adding %s: %s", name, error)
            failed.append(f"{name}: unexpected error")

    if meetup is not None:
        await refresh_callup_messages(context.bot, settings, container, meetup)

    lines = []
    if added:
        lines.append("Added: " + ", ".join(added))
    if failed:
        lines.append("Failed:\n" + "\n".join(f"  • {f}" for f in failed))
    await message.reply_text("\n".join(lines) if lines else "Nothing to do.")


@log_func
@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 3:
        await message.reply_text(
            r"Usage: `/remove_player` `YYYY/MM/DD HH:MM` `<player_name>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    date_str = f"{args[0]} {args[1]}"
    player_name = " ".join(args[2:])

    settings = context.bot_data["settings"]
    try:
        meetup = container.remove_player_from_meetup().execute(date_str, player_name)
        await refresh_callup_messages(context.bot, settings, container, meetup)
        await message.reply_text("Player removed from meetup!")
    except ValueError as error:
        await message.reply_text(str(error))
    except MeetupError as error:
        logger.error("Meetup error removing player: %s", error)
        await message.reply_text("Meetup error. Please try again.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error removing player from meetup: %s", error)
        await message.reply_text("Telegram error. Please try again.")
    except Exception as error:
        logger.exception("Error removing player from meetup: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@log_func
@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_teams command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            r"Usage: `/create_teams` `YYYY/MM/DD HH:MM`", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    date_str = f"{args[0]} {args[1]}"

    settings = context.bot_data["settings"]
    try:
        meetup = container.create_teams().execute(date_str)

        if not meetup.teams:
            await message.reply_text("No teams created.")
            return

        await refresh_callup_messages(
            context.bot, settings, container, meetup, include_keyboard=False
        )

        await message.reply_text("Equipos creados ✅")
    except InvalidMeetupDateError as error:
        await message.reply_text(str(error))
    except MeetupError as error:
        logger.error("Meetup error creating teams: %s", error)
        await message.reply_text("Meetup error. Please try again.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error creating teams: %s", error)
        await message.reply_text("Telegram error. Please try again.")
    except Exception as error:
        logger.exception("Error creating teams: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@log_func
@authorized
async def list_meetups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_meetups command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    meetups = container.meetup_repository.find_all()

    if not meetups:
        await message.reply_text("No meetups found.")
        return

    lines = ["*Meetups:*"]
    for m in meetups:
        lines.append(
            rf"\- `{m.date.strftime('%Y/%m/%d %H:%M')}` at {m.location.replace('-', r'\-')}"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@log_func
@authorized
async def show_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /show_meetup command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            text=r"Usage: `/show_meetup` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        meetup_date = datetime.strptime(f"{args[0]} {args[1]}", "%Y/%m/%d %H:%M")
    except ValueError:
        await message.reply_text(
            text=r"Invalid date format\. Use: `/show_meetup` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    meetup = container.meetup_repository.find_by_date(meetup_date.date())
    if not meetup:
        await message.reply_text("Meetup not found.")
        return

    settings: Settings = context.bot_data["settings"]
    player_names = _get_player_names(container.player_repository)
    text = format_main_message(
        meetup, player_names, team_display_names=settings.pyball.team_display_names
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


@log_func
@authorized
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command - send substitutes message."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]

    args = context.args
    if not args:
        await message.reply_text(
            text="Usage: `/search` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        meetup_date = datetime.strptime(f"{args[0]} {args[1]}", "%Y/%m/%d %H:%M")
    except ValueError:
        await message.reply_text(
            text=r"Invalid date\. Use: `/search` `YYYY/MM/DD HH:MM`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    meetup = container.meetup_repository.find_by_date(meetup_date.date())

    if not meetup:
        await message.reply_text("Meetup not found.")
        return

    if not settings.telegram.substitutes.chat_id:
        await message.reply_text("Substitutes chat not configured.")
        return

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}
    text = format_subs_message(
        meetup, player_names, player_groups, team_display_names=settings.pyball.team_display_names
    )
    keyboard = build_subs_keyboard(meetup.date)

    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.substitutes.chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        store = TelegramMessageStore(settings.paths.bot_messages_file)
        store.save_message(
            meetup.date,
            "substitute",
            MessageTracking(
                chat_id=settings.telegram.substitutes.chat_id,
                message_id=msg.message_id,
            ),
        )

        await message.reply_text("Substitutes message sent!")
    except telegram.error.TelegramError as error:
        logger.error("Error sending substitutes message (Telegram): %s", error)
        await message.reply_text("Telegram error. Failed to send message.")
    except Exception as error:
        logger.exception("Error sending substitutes message: %s", error)
        await message.reply_text("Failed to send message.")


@log_func
@authorized
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command — send a stats image for the requested scope."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or args[0] not in ("temporada", "historico"):
        await message.reply_text(
            text="Usa `/stats temporada` o `/stats historico`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    scope = "season" if args[0] == "temporada" else "alltime"
    container: Container = context.bot_data["container"]
    telegram_settings: TelegramSettings = context.bot_data["settings"].telegram

    message_thread_id: str | int | None = None
    if message.chat_id == telegram_settings.regulars.chat_id:
        message_thread_id = telegram_settings.regulars.stats_thread_id

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
            message_thread_id=int(message_thread_id) if message_thread_id else None,
            photo=png,
            caption=caption,
        )
    except Exception as error:
        logger.exception("Error sending stats: %s", error)
        await message.reply_text("Error al generar las estadísticas.")


def _get_player_names(player_repo) -> dict:
    """Build a {str_uuid: name} lookup dict for all players."""
    all_players = player_repo.find_all()
    return {str(p.id.value): p.name for p in all_players}
