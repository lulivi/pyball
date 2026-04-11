"""Meetup command handlers."""

import logging

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.meetup.create_meetup import DuplicateMeetupError
from pyball.application.meetup.create_teams import InvalidMeetupDateError
from pyball.bot.auth import authorized
from pyball.bot.formatters import (
    build_main_keyboard,
    build_subs_keyboard,
    format_main_message,
    format_subs_message,
)
from pyball.infrastructure import TelegramMessageStore
from pyball.infrastructure.telegram_store import MessageTracking
from pyball.settings import load_settings

logger = logging.getLogger(__name__)


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


@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_meetup command - creates meetup and sends callup messages."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args:
        await message.reply_text("Usage: /new_meetup YYYY-MM-DD HH:MM")
        return

    try:
        date_str = " ".join(args)
        date = datetime.fromisoformat(date_str)
    except ValueError:
        await message.reply_text("Invalid date format. Use: /new_meetup YYYY-MM-DD HH:MM")
        return

    await _create_meetup_and_send(date, update, context)


@authorized
async def next_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /next_meetup command - creates meetup for next default weekday and sends callup."""
    message = update.message
    if message is None:
        return

    settings = load_settings()
    next_date = _get_next_weekday(settings.pyball.default_week_day)
    day_name = next_date.strftime("%A")
    await message.reply_text(
        f"Creating meetup for {next_date.strftime('%Y-%m-%d %H:%M')} ({day_name})..."
    )
    await _create_meetup_and_send(next_date, update, context)


async def _create_meetup_and_send(
    date: datetime, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create meetup and send callup messages. Shared by new_meetup and next_meetup."""
    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    message = update.message
    settings = load_settings()

    try:
        meetup = container.create_meetup().execute(date, settings.pyball.location)
    except DuplicateMeetupError:
        if message is not None:
            await message.reply_text(
                f"Meetup already exists at {date.strftime('%Y-%m-%d %H:%M')}."
            )
        return
    except InvalidMeetupDateError as error:
        if message is not None:
            await message.reply_text(str(error))
        return
    except Exception as error:
        logger.exception("Error creating meetup: %s", error)
        if message is not None:
            await message.reply_text("An error occurred. Please try again.")
        return

    await _send_callup_messages(context, settings, container, meetup)
    if message is not None:
        await message.reply_text("Meetup created and callup sent!")


async def _send_callup_messages(context, settings, container, meetup) -> None:
    """Send callup messages to regulars and substitutes chats."""
    player_repo = container.player_repository
    all_players = player_repo.find_all()
    player_names = {str(player.id.value): player.name for player in all_players}
    player_groups = {str(player.id.value): player.group for player in all_players}

    text = format_main_message(meetup, player_names, player_groups)
    keyboard = build_main_keyboard(meetup.date)

    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.regulars.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.regulars.thread_id or None,
            parse_mode="MarkdownV2",
        )

        store = TelegramMessageStore(settings.paths.bot_messages_file)
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "regular",
            MessageTracking(
                chat_id=settings.telegram.regulars.chat_id,
                thread_id=settings.telegram.regulars.thread_id or None,
                message_id=msg.message_id,
            ),
        )
    except Exception as error:
        logger.exception("Error sending regulars message: %s", error)

    if settings.telegram.substitutes.chat_id:
        subs_text = format_subs_message(meetup, player_names, player_groups)
        subs_keyboard = build_subs_keyboard(meetup.date)

        try:
            msg = await context.bot.send_message(
                chat_id=settings.telegram.substitutes.chat_id,
                text=subs_text,
                reply_markup=subs_keyboard,
                message_thread_id=settings.telegram.substitutes.thread_id or None,
                parse_mode="HTML",
            )

            store = TelegramMessageStore(settings.paths.bot_messages_file)
            store.save_message(
                meetup.date.strftime("%Y-%m-%dT%H:%M"),
                "substitute",
                MessageTracking(
                    chat_id=settings.telegram.substitutes.chat_id,
                    thread_id=settings.telegram.substitutes.thread_id or None,
                    message_id=msg.message_id,
                ),
            )
        except Exception as error:
            logger.exception("Error sending substitutes message: %s", error)


def _get_next_weekday(default_week_day: str) -> datetime:
    """Calculate next occurrence of default weekday."""
    settings = load_settings()
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    target_weekday = day_map.get(default_week_day.lower(), 2)

    today = datetime.now()
    days_until_target = (target_weekday - today.weekday() + 7) % 7

    if days_until_target == 0:
        days_until_target = 7

    next_date = today + timedelta(days=days_until_target)
    hour, minute = map(int, settings.pyball.default_hour.split(":"))
    return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_player command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text("Usage: /add_player YYYY-MM-DD HH:MM <player_name>")
        return

    date_str = args[0]
    player_name = " ".join(args[1:])

    try:
        container.add_player_to_meetup().execute(date_str, player_name)
        await message.reply_text("Player added!")
    except ValueError as error:
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error adding player to meetup: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove_player command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text("Usage: /remove_player YYYY-MM-DD HH:MM <player_name>")
        return

    date_str = args[0]
    player_name = " ".join(args[1:])

    try:
        container.remove_player_from_meetup().execute(date_str, player_name)
        await message.reply_text("Player removed from meetup!")
    except ValueError as error:
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error removing player from meetup: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_teams command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if not args:
        await message.reply_text("Usage: /create_teams YYYY-MM-DD HH:MM")
        return

    date_str = " ".join(args)

    try:
        meetup = container.create_teams().execute(date_str)

        if not meetup.teams:
            await message.reply_text("No teams created.")
            return

        player_names = _get_player_names(None, container.player_repository)
        lines = ["*Teams:*"]
        for team in meetup.teams:
            lines.append(f"\n{team.name}:")
            for player_id in team.players:
                name = player_names.get(player_id, str(player_id.value))
                lines.append(f"  - {name}")

        await message.reply_text("\n".join(lines))
    except InvalidMeetupDateError as error:
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error creating teams: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def list_meetups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_meetups command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    meetups = container.meetup_repository.find_all()

    if not meetups:
        await message.reply_text("No meetups found.")
        return

    lines = ["*Meetups:*"]
    for m in meetups:
        lines.append(f"- {m.date.strftime('%Y-%m-%d %H:%M')} at {m.location}")

    await message.reply_text("\n".join(lines))


@authorized
async def show_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /show_meetup command."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    args = context.args
    if not args:
        await message.reply_text("Usage: /show_meetup YYYY-MM-DD HH:MM")
        return

    date_str = " ".join(args)

    try:
        meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.reply_text("Invalid date format. Use: YYYY-MM-DD HH:MM")
        return

    all_meetups = container.meetup_repository.find_all()
    meetup = None
    for m in all_meetups:
        if m.date == meetup_date:
            meetup = m
            break

    if not meetup:
        await message.reply_text("Meetup not found.")
        return

    player_names = _get_player_names(None, container.player_repository)
    lines = [f"*Meetup: {meetup.date.strftime('%Y-%m-%d %H:%M')}*"]
    lines.append(f"📍 {meetup.location}")

    if meetup.players:
        lines.append("\n*Players:*")
        for player_id in meetup.players:
            name = player_names.get(player_id, str(player_id.value))
            lines.append(f"  - {name}")
    else:
        lines.append("\nNo players yet.")

    await message.reply_text("\n".join(lines))


@authorized
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command - send substitutes message."""
    message = update.message
    if message is None:
        return

    container: Container | None = context.bot_data.get("container")
    if container is None:
        container = Container()

    settings = load_settings()

    args = context.args
    if not args:
        await message.reply_text("Usage: /search YYYY-MM-DD")
        return

    date_str = args[0]

    try:
        meetup_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.reply_text("Invalid date. Use: /search YYYY-MM-DD")
        return

    meetup = None
    for m in container.meetup_repository.find_all():
        if m.date.date() == meetup_date.date():
            meetup = m
            break

    if not meetup:
        await message.reply_text("Meetup not found.")
        return

    if not settings.telegram.substitutes.chat_id:
        await message.reply_text("Substitutes chat not configured.")
        return

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}
    text = format_subs_message(meetup, player_names, player_groups)
    keyboard = build_subs_keyboard(meetup.date)

    thread_id = settings.telegram.substitutes.thread_id
    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.substitutes.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=int(thread_id) if thread_id else None,
            parse_mode="MarkdownV2",
        )

        store = TelegramMessageStore(settings.paths.bot_messages_file)
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "substitute",
            MessageTracking(
                chat_id=settings.telegram.substitutes.chat_id,
                thread_id=thread_id or None,
                message_id=msg.message_id,
            ),
        )

        await message.reply_text("Substitutes message sent!")
    except Exception as error:
        logger.exception("Error sending substitutes message: %s", error)
        await message.reply_text("Failed to send message.")


def _get_player_names(player_ids, player_repo) -> dict:
    """Build a player name lookup dict, fetching all players at once."""
    all_players = player_repo.find_all()
    return {p.id: p.name for p in all_players}
