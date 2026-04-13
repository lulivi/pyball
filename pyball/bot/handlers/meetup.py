"""Meetup command handlers."""

import logging

from datetime import datetime, timedelta

import telegram

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
from pyball.exceptions import MeetupError
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.message_store import MessageTracking
from pyball.settings import PyballSettings

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
    application.add_handler(CommandHandler("start_match", start_match_handler))


async def close_match_messages(
    bot,
    message_store,
    meetup,
    player_names: dict,
    player_groups: dict,
) -> None:
    """Edit callup messages to show final score and remove join/leave buttons.

    Args:
        bot: Telegram Bot instance.
        message_store: TelegramMessageStore to look up tracked message IDs.
        meetup: Meetup with result already set.
        player_names: Dict of str(UUID) -> player name.
        player_groups: Dict of str(UUID) -> player group.
    """
    date_key = meetup.date.strftime("%Y-%m-%dT%H:%M")

    regular_tracking = message_store.get_message(date_key, "regular")
    if regular_tracking:
        text = format_main_message(meetup, player_names)
        try:
            await bot.edit_message_text(
                chat_id=regular_tracking.chat_id,
                message_id=regular_tracking.message_id,
                text=text,
                reply_markup=None,
                parse_mode="MarkdownV2",
            )
            message_store.delete_message(date_key, "regular")
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit regulars message: %s", error)

    sub_tracking = message_store.get_message(date_key, "substitute")
    if sub_tracking:
        text = format_subs_message(meetup, player_names, player_groups)
        try:
            await bot.edit_message_text(
                chat_id=sub_tracking.chat_id,
                message_id=sub_tracking.message_id,
                text=text,
                reply_markup=None,
                parse_mode="MarkdownV2",
            )
            message_store.delete_message(date_key, "substitute")
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit substitutes message: %s", error)


@authorized
async def start_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start_match command — generate match URL and reply to admins only."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text("Usage: /start_match `YYYY/MM/DD HH:MM`")
        return

    date_str = f"{args[0]} {args[1]}"
    container: Container = context.bot_data["container"]

    try:
        url = container.start_match().execute(date_str)
        await message.reply_text(
            f"🔗 Enlace del partido:\n{url}",
            disable_web_page_preview=True,
        )
    except ValueError as error:
        await message.reply_text(str(error))
    except MeetupError as error:
        logger.error("Meetup error starting match: %s", error)
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error starting match: %s", error)
        await message.reply_text("An error occurred. Please try again.")


@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_meetup command - creates meetup and sends callup messages."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text("Usage: /new_meetup `YYYY/MM/DD HH:MM`")
        return

    try:
        date = datetime.strptime(f"{args[0]} {args[1]}", "%Y/%m/%d %H:%M")
    except ValueError:
        await message.reply_text("Invalid date format. Use: /new_meetup `YYYY/MM/DD HH:MM`")
        return

    await _create_meetup_and_send(date, update, context)


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
        f"Creating meetup for `{next_date.strftime('%Y/%m/%d %H:%M')}` ({day_name})..."
    )
    await _create_meetup_and_send(next_date, update, context)


async def _create_meetup_and_send(
    date: datetime, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create meetup and send callup messages. Shared by new_meetup and next_meetup."""
    container: Container = context.bot_data["container"]
    message = update.message
    settings = context.bot_data["settings"]

    try:
        meetup = container.create_meetup().execute(date, settings.pyball.location)
    except DuplicateMeetupError:
        if message is not None:
            await message.reply_text(
                f"Meetup already exists at `{date.strftime('%Y/%m/%d %H:%M')}`."
            )
        return
    except InvalidMeetupDateError as error:
        if message is not None:
            await message.reply_text(str(error))
        return
    except MeetupError as error:
        logger.error("Error creating meetup (domain): %s", error)
        if message is not None:
            await message.reply_text("Meetup error. Please try again.")
        return
    except telegram.error.TelegramError as error:
        logger.error("Error creating meetup (Telegram): %s", error)
        if message is not None:
            await message.reply_text("Telegram error. Please try again.")
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

    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)

    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.regulars.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.regulars.meetups_thread_id or None,
            parse_mode="MarkdownV2",
        )

        store = TelegramMessageStore(settings.paths.bot_messages_file)
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
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


def _get_next_weekday(pyball_settings: PyballSettings) -> datetime:
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


@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 3:
        await message.reply_text("Usage: /add_player `YYYY/MM/DD HH:MM` <name1>, <name2>, ...")
        return

    date_str = f"{args[0]} {args[1]}"
    names = [n.strip() for n in " ".join(args[2:]).split(",") if n.strip()]

    if not names:
        await message.reply_text("Usage: /add_player `YYYY/MM/DD HH:MM` <name1>, <name2>, ...")
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
        await _refresh_callup_messages(context, settings, container, meetup)

    lines = []
    if added:
        lines.append("Added: " + ", ".join(added))
    if failed:
        lines.append("Failed:\n" + "\n".join(f"  • {f}" for f in failed))
    await message.reply_text("\n".join(lines) if lines else "Nothing to do.")


@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 3:
        await message.reply_text("Usage: /remove_player `YYYY/MM/DD HH:MM` <player_name>")
        return

    date_str = f"{args[0]} {args[1]}"
    player_name = " ".join(args[2:])

    settings = context.bot_data["settings"]
    try:
        meetup = container.remove_player_from_meetup().execute(date_str, player_name)
        await _refresh_callup_messages(context, settings, container, meetup)
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


@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_teams command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text("Usage: /create_teams `YYYY/MM/DD HH:MM`")
        return

    date_str = f"{args[0]} {args[1]}"

    settings = context.bot_data["settings"]
    try:
        meetup = container.create_teams().execute(date_str)

        if not meetup.teams:
            await message.reply_text("No teams created.")
            return

        all_players = container.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}
        player_groups = {str(p.id.value): p.group for p in all_players}

        date_key = meetup.date.strftime("%Y-%m-%dT%H:%M")
        store = TelegramMessageStore(settings.paths.bot_messages_file)

        regular_tracking = store.get_message(date_key, "regular")
        if regular_tracking:
            text = format_main_message(meetup, player_names)
            try:
                await context.bot.edit_message_text(
                    chat_id=regular_tracking.chat_id,
                    message_id=regular_tracking.message_id,
                    text=text,
                    reply_markup=None,
                    parse_mode="MarkdownV2",
                )
            except telegram.error.BadRequest as err:
                logger.warning("Could not edit regulars message after teams: %s", err)

        sub_tracking = store.get_message(date_key, "substitute")
        if sub_tracking:
            subs_text = format_subs_message(meetup, player_names, player_groups)
            try:
                await context.bot.edit_message_text(
                    chat_id=sub_tracking.chat_id,
                    message_id=sub_tracking.message_id,
                    text=subs_text,
                    reply_markup=None,
                    parse_mode="MarkdownV2",
                )
            except telegram.error.BadRequest as err:
                logger.warning("Could not edit substitutes message after teams: %s", err)

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
        lines.append(f"- `{m.date.strftime('%Y/%m/%d %H:%M')}` at {m.location}")

    await message.reply_text("\n".join(lines))


@authorized
async def show_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /show_meetup command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text("Usage: /show_meetup `YYYY/MM/DD HH:MM`")
        return

    try:
        meetup_date = datetime.strptime(f"{args[0]} {args[1]}", "%Y/%m/%d %H:%M")
    except ValueError:
        await message.reply_text("Invalid date format. Use: /show_meetup `YYYY/MM/DD HH:MM`")
        return

    meetup = container.meetup_repository.find_by_date(meetup_date.date())
    if not meetup:
        await message.reply_text("Meetup not found.")
        return

    player_names = _get_player_names(container.player_repository)
    lines = [f"*Meetup: `{meetup.date.strftime('%Y/%m/%d %H:%M')}`*"]
    lines.append(f"📍 {meetup.location}")

    if meetup.players:
        lines.append("\n*Players:*")
        for player_id in meetup.players:
            name = player_names.get(str(player_id.value), str(player_id.value))
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

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]

    args = context.args
    if not args:
        await message.reply_text("Usage: /search `YYYY/MM/DD`")
        return

    try:
        meetup_date = datetime.strptime(args[0], "%Y/%m/%d")
    except ValueError:
        await message.reply_text("Invalid date. Use: /search `YYYY/MM/DD`")
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
    text = format_subs_message(meetup, player_names, player_groups)
    keyboard = build_subs_keyboard(meetup.date)

    thread_id = settings.telegram.substitutes.meetups_thread_id
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
    except telegram.error.TelegramError as error:
        logger.error("Error sending substitutes message (Telegram): %s", error)
        await message.reply_text("Telegram error. Failed to send message.")
    except Exception as error:
        logger.exception("Error sending substitutes message: %s", error)
        await message.reply_text("Failed to send message.")


def _get_player_names(player_repo) -> dict:
    """Build a {str_uuid: name} lookup dict for all players."""
    all_players = player_repo.find_all()
    return {str(p.id.value): p.name for p in all_players}


async def _refresh_callup_messages(context, settings, container, meetup) -> None:
    """Edit the existing callup messages to reflect the current player list."""
    player_repo = container.player_repository
    all_players = player_repo.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}

    date_key = meetup.date.strftime("%Y-%m-%dT%H:%M")
    store = TelegramMessageStore(settings.paths.bot_messages_file)

    regular_tracking = store.get_message(date_key, "regular")
    if regular_tracking:
        text = format_main_message(meetup, player_names)
        keyboard = build_main_keyboard(meetup.date)
        try:
            await context.bot.edit_message_text(
                chat_id=regular_tracking.chat_id,
                message_id=regular_tracking.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit regulars message: %s", error)

    sub_tracking = store.get_message(date_key, "substitute")
    if sub_tracking:
        text = format_subs_message(meetup, player_names, player_groups)
        keyboard = build_subs_keyboard(meetup.date)
        try:
            await context.bot.edit_message_text(
                chat_id=sub_tracking.chat_id,
                message_id=sub_tracking.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit substitutes message: %s", error)
