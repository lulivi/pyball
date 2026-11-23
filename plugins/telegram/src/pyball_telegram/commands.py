"""The bot's commands: /help for everyone, the rest for admins only."""

from __future__ import annotations

import functools
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine

import telegram
from pyball_client import ApiError
from telegram import BotCommand, Message, Update
from telegram.constants import ParseMode, ReactionEmoji
from telegram.ext import Application, CommandHandler, ContextTypes

from pyball_telegram.api import ACTIVE, MEETUPS, PLAYERS, STATS, Meetup
from pyball_telegram.callups import Callups
from pyball_telegram.formatters import format_display, parse_display
from pyball_telegram.fuzzy import match_player
from pyball_telegram.state import LinkStore

logger = logging.getLogger(__name__)

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]

DESCRIPTIONS: dict[str, str] = {
    "help": "Show this message",
    "player_link": "Link Telegram ID to player",
    "player_unlink": "Unlink a player's Telegram ID",
    "meetup_show": "Repost the current convocatoria",
    "meetup_stats": "Show statistics",
}

_MD_V2_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def setup_commands(application: Application[Any, Any, Any, Any, Any, Any]) -> None:
    """Register every command under its name and its short alias (p_..., m_...)."""
    handlers: dict[str, Handler] = {
        "help": help_command,
        "player_link": _admin(link_command),
        "player_unlink": _admin(unlink_command),
        "meetup_show": _admin(show_command),
        "meetup_stats": _admin(stats_command),
    }
    for name, handler in handlers.items():
        alias = short_alias(name)
        application.add_handler(
            CommandHandler([name] if alias is None else [name, alias], handler)
        )


async def register_commands(bot: telegram.Bot) -> None:
    """Publish the command menu."""
    await bot.set_my_commands([BotCommand(name, desc) for name, desc in DESCRIPTIONS.items()])


def short_alias(name: str) -> str | None:
    """Return the abbreviated alias of a grouped command, or None."""
    for prefix, short in (("player_", "p_"), ("meetup_", "m_")):
        if name.startswith(prefix):
            return short + name[len(prefix) :]
    return None


async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the command list."""
    if update.message is not None:
        await update.message.reply_text(_render_help(), parse_mode=ParseMode.MARKDOWN_V2)


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_link <name>, <telegram id>: let that Telegram user use the buttons."""
    message = _message(update)
    callups = _callups(context)
    name, _, raw_id = " ".join(context.args or []).partition(",")
    if not name.strip() or not raw_id.strip():
        await message.reply_text(
            r"Usage: `/player_link` `<player_name>, <telegram_id>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    try:
        telegram_id = int(raw_id.strip())
    except ValueError:
        await message.reply_text("ID de Telegram no válido. Debe ser un número.")
        return
    try:
        player = match_player(name, await callups.api.call(PLAYERS))
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return
    links = LinkStore(callups.config.mapping_file)
    linked = links.player_id(telegram_id)
    if linked == player.id:
        await message.reply_text("Este ID de Telegram ya está vinculado a este jugador.")
    elif linked:
        await message.reply_text(
            "Este ID de Telegram ya está vinculado a otro jugador. "
            "Elimina el enlace primero con /player_unlink <player_name>"
        )
    else:
        links.link(telegram_id, player.id)
        await _react_ok(context.bot, message)


async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_unlink <name>: remove the player's Telegram link."""
    message = _message(update)
    callups = _callups(context)
    name = " ".join(context.args or []).strip()
    if not name:
        await message.reply_text(
            r"Usage: `/player_unlink` `<player_name>`", parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    try:
        player = match_player(name, await callups.api.call(PLAYERS))
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return
    links = LinkStore(callups.config.mapping_file)
    telegram_id = links.telegram_id(player.id)
    if telegram_id is None:
        await message.reply_text("Este jugador no está vinculado a ningún ID de Telegram.")
        return
    links.unlink(telegram_id)
    await _react_ok(context.bot, message)


async def show_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meetup_show [date]: repost the callup of the active meetup, or of that date."""
    message = _message(update)
    callups = _callups(context)
    meetup = await _resolve_meetup(message, context.args or [], callups)
    if meetup is None:
        return
    try:
        await callups.send_regulars(meetup)
        _, groups = await callups.players()
        has_substitutes = any(groups.get(p) == "substitute" for p in meetup.players)
        if has_substitutes and callups.config.substitutes_meetups:
            await callups.send_substitutes(meetup)
        await _react_ok(context.bot, message)
    except ApiError:
        logger.exception("Could not show the meetup")
        await message.reply_text("Error al mostrar la convocatoria.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /meetup_stats temporada|historico: send that stats image here."""
    message = _message(update)
    callups = _callups(context)
    args = context.args or []
    if not args or args[0] not in ("temporada", "historico"):
        await message.reply_text(
            "Usa `/meetup_stats temporada` o `/meetup_stats historico`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    season = args[0] == "temporada"
    stats_chat = callups.config.regulars_stats
    thread = stats_chat.thread_id if message.chat_id == stats_chat.chat_id else None
    try:
        png = await callups.api.call(STATS, params={"scope": "season" if season else "alltime"})
        await context.bot.send_photo(
            chat_id=message.chat_id,
            message_thread_id=thread,
            photo=png,
            caption="📊 Esta temporada" if season else "📊 Histórico",
        )
        await _react_ok(context.bot, message)
    except (ApiError, telegram.error.TelegramError):
        logger.exception("Could not send the stats")
        await message.reply_text("Error al generar las estadísticas.")


def _admin(handler: Handler) -> Handler:
    """Run ``handler`` only for admins; tell anyone else they may not."""

    @functools.wraps(handler)
    async def guarded(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None or update.message is None:
            return
        if not _callups(context).config.is_admin(user.id):
            logger.warning("Unauthorized command from user ID %s", user.id)
            await update.message.reply_text(
                "Unauthorized. You don't have permission to run this command."
            )
            return
        await handler(update, context)

    return guarded


async def _resolve_meetup(message: Message, args: list[str], callups: Callups) -> Meetup | None:
    """Return the meetup at the date in ``args``, or the active one; reply if there is none."""
    fmt = callups.settings.display_date_format
    if len(args) >= 2:
        try:
            date = parse_display(f"{args[0]} {args[1]}", fmt)
        except ValueError:
            await message.reply_text(_date_usage(fmt), parse_mode=ParseMode.MARKDOWN_V2)
            return None
        found = await callups.api.call(MEETUPS, params={"date": date.isoformat()})
        if not found:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return None
        return found[0]
    meetup = await callups.api.call_optional(ACTIVE)
    if meetup is None:
        await message.reply_text("No hay ningún partido activo.")
    return meetup


def _date_usage(fmt: str) -> str:
    example = format_display(datetime.now(), fmt)
    return (
        r"Formato de fecha no válido\."
        "\n"
        rf"Formato: `{fmt}`"
        "\n"
        rf"Ejemplo: `/meetup_show` `{example}`"
    )


async def _react_ok(bot: telegram.Bot, message: Message) -> None:
    """React 👌 to ``message``, or reply 👌 where reactions are not allowed."""
    try:
        await bot.set_message_reaction(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reaction=ReactionEmoji.OK_HAND_SIGN,
        )
    except telegram.error.TelegramError as error:
        logger.warning("Could not react to %s: %s", message.message_id, error)
        await message.reply_text(ReactionEmoji.OK_HAND_SIGN)


def _render_help() -> str:
    lines = [r"*Available Commands:*"]
    category = None
    for name, desc in DESCRIPTIONS.items():
        current = _category(name)
        if current != category:
            lines.extend(["", rf"*{current}:*"])
            category = current
        lines.append(rf"`/{name}` \- {_escape(desc)}")
    return "\n".join(lines)


def _category(name: str) -> str:
    if name.startswith("player_"):
        return "Player"
    if name.startswith("meetup_"):
        return "Meetup"
    return "General"


def _escape(text: str) -> str:
    return "".join(f"\\{ch}" if ch in _MD_V2_SPECIAL else ch for ch in text)


def _message(update: Update) -> Message:
    assert update.message is not None  # _admin lets only messages through
    return update.message


def _callups(context: ContextTypes.DEFAULT_TYPE) -> Callups:
    callups: Callups = context.bot_data["callups"]
    return callups
