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
from datetime import datetime, timedelta
from io import BytesIO

import qrcode
import telegram
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.meetup import DuplicateMeetupError
from pyball.application.meetup.compute_stats import ComputeStats
from pyball.domain.meetup.errors import (
    MeetupHasNoTeamsError,
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    UnknownAlgorithmError,
)
from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.bot.auth import authorized
from pyball.infrastructure.telegram.bot.reactions import react_ok
from pyball.infrastructure.telegram.formatters import (
    build_main_keyboard,
    build_subs_keyboard,
    format_display,
    format_main_message,
    format_subs_message,
    parse_display,
)
from pyball.infrastructure.telegram.message_store import MessageTracking
from pyball.infrastructure.telegram.notifications import refresh_callup_messages
from pyball.infrastructure.telegram.settings import TelegramAppSettings, TelegramSettings
from pyball.logger import log_func
from pyball.settings import PyballConfig

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
    application.add_handler(CommandHandler("lock", lock_handler))
    application.add_handler(CommandHandler("unlock", unlock_handler))
    application.add_handler(CommandHandler("match_qr", match_qr_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(CommandHandler("change_location", change_location_handler))
    application.add_handler(CommandHandler("change_date", change_date_handler))


@log_func
@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_meetup command - creates meetup and sends callup messages."""
    message = update.message
    if message is None:
        return

    settings: TelegramAppSettings = context.bot_data["settings"]
    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(
            _date_usage_msg("new_meetup", settings.pyball.display_date_format),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        date = parse_display(f"{args[0]} {args[1]}", settings.pyball.display_date_format)
    except ValueError:
        await message.reply_text(
            _date_usage_msg("new_meetup", settings.pyball.display_date_format),
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
    await _create_meetup_and_send(next_date, update, context)


@log_func
@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_player command."""
    message = update.message
    if message is None:
        return
    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    args = context.args or []

    meetup_date, name_args = _try_parse_date_args(args, settings.pyball.display_date_format)

    if meetup_date is not None:
        meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return
    else:
        meetup = await _resolve_meetup(message, [], settings, container, "add_player")
        if meetup is None:
            return

    names = [n.strip() for n in " ".join(name_args).split(",") if n.strip()]
    if not names:
        await message.reply_text(
            _date_usage_msg(
                "add_player",
                settings.pyball.display_date_format,
                r"`<name1>`, `<name2>`, \.\.\.",
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    use_case = container.add_player_to_meetup()
    failed: list[str] = []
    updated_meetup = None
    for name in names:
        try:
            updated_meetup = use_case.execute(meetup.date, name)
            meetup = updated_meetup
        except MeetupNotFoundError:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return
        except ValueError as error:
            failed.append(f"{name}: {error}")
        except Exception:
            logger.exception("Unexpected error adding player '%s' to meetup", name)
            failed.append(f"{name}: error inesperado")

    if updated_meetup is not None:
        await refresh_callup_messages(context.bot, settings, container, updated_meetup)

    if failed:
        await message.reply_text("Fallidos:\n" + "\n".join(f"  • {f}" for f in failed))
    else:
        await react_ok(context.bot, message)


@log_func
@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    args = context.args or []

    meetup_date, name_args = _try_parse_date_args(args, settings.pyball.display_date_format)

    if meetup_date is not None:
        meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return
        player_name = " ".join(name_args)
    else:
        meetup = await _resolve_meetup(message, [], settings, container, "remove_player")
        if meetup is None:
            return
        player_name = " ".join(name_args)

    if not player_name:
        await message.reply_text(
            _date_usage_msg(
                "remove_player",
                settings.pyball.display_date_format,
                r"`<player_name>`",
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        meetup = container.remove_player_from_meetup().execute(meetup.date, player_name)
        await refresh_callup_messages(context.bot, settings, container, meetup)
        await react_ok(context.bot, message)
    except ValueError:
        await message.reply_text(
            _date_usage_msg(
                "remove_player",
                settings.pyball.display_date_format,
                r"`<player_name>`",
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except MeetupNotFoundError:
        await message.reply_text("No existe ningún meetup para esa fecha.")
    except PlayerNotInMeetupError:
        await message.reply_text("El jugador no está en este meetup.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error removing player from meetup: %s", error)
        await message.reply_text("Error de Telegram. Inténtalo de nuevo.")
    except Exception:
        logger.exception("Unexpected error removing player from meetup")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /create_teams [fecha] [hora] [algoritmo] command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings = context.bot_data["settings"]
    usage = _date_usage_msg(
        "create_teams",
        settings.pyball.display_date_format,
        suffix=(
            r"\[algoritmo\]"
            "\n"
            r"• `balanceado` \- por defecto"
            "\n"
            r"• `manual Nombre1,Nombre2;Nombre3,Nombre4` \- equipos manuales"
        ),
    )

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return

    date_str = f"{args[0]} {args[1]}"
    algo_name = args[2] if len(args) > 2 else None

    try:
        meetup_date = parse_display(date_str, settings.pyball.display_date_format)
    except ValueError:
        await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return

    try:
        if algo_name == "manual":
            teams = await _parse_manual_teams(message, args, usage)
            if teams is None:
                return
            team_a_names, team_b_names = teams
            meetup = container.create_teams_manually().execute(
                meetup_date, team_a_names, team_b_names
            )
            if not meetup.teams:
                await message.reply_text("No se han creado equipos.")
                return
            await refresh_callup_messages(context.bot, settings, container, meetup)
        else:
            meetup = await _do_create_teams(
                meetup_date, container, context.bot, settings, algo_name
            )
            if not meetup.teams:
                await message.reply_text("No se han creado equipos.")
                return

        await react_ok(context.bot, message)
    except ValueError as error:
        await message.reply_text(str(error))
    except UnknownAlgorithmError as error:
        available = ", ".join(error.available)
        await message.reply_text(f"Algoritmo '{error.name}' no existe. Disponibles: {available}")
    except MeetupNotFoundError:
        await message.reply_text("No existe ningún meetup para esa fecha.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error creating teams: %s", error)
        await message.reply_text("Error de Telegram. Inténtalo de nuevo.")
    except Exception:
        logger.exception("Unexpected error creating teams")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def list_meetups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_meetups command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings: TelegramAppSettings = context.bot_data["settings"]

    meetups = container.meetup_repository.find_all()

    if not meetups:
        await message.reply_text("No hay meetups registrados.")
        return

    lines = ["*Meetups:*"]
    for m in meetups:
        date_str = format_display(m.date, settings.pyball.display_date_format)
        lines.append(rf"\- `{date_str}` en {m.location.replace('-', r'\-')}")

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
    settings: TelegramAppSettings = context.bot_data["settings"]

    meetup = await _resolve_meetup(message, context.args, settings, container, "show_meetup")
    if meetup is None:
        return

    player_names = _get_player_names(container.player_repository)
    text = format_main_message(
        meetup,
        player_names,
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
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

    if not settings.telegram.substitutes.chat_id:
        await message.reply_text("El chat de suplentes no está configurado.")
        return

    meetup = await _resolve_meetup(message, context.args, settings, container, "search")
    if meetup is None:
        return

    player_repo = container.player_repository
    player_names = _get_player_names(player_repo)
    player_groups = {str(p.id.value): p.group for p in player_repo.find_all()}
    text = format_subs_message(
        meetup,
        player_names,
        player_groups,
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
    )
    keyboard = build_subs_keyboard(meetup.date)

    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.substitutes.chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
        store.save_message(
            meetup.date,
            "substitute",
            MessageTracking(
                chat_id=settings.telegram.substitutes.chat_id,
                message_id=msg.message_id,
            ),
        )
        await react_ok(context.bot, message)
    except telegram.error.TelegramError as error:
        logger.error("Telegram error sending substitutes message: %s", error)
        await message.reply_text("Error de Telegram al enviar el mensaje.")
    except Exception:
        logger.exception("Unexpected error sending substitutes message")
        await message.reply_text("Error al enviar el mensaje.")


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
        await react_ok(context.bot, message)
    except Exception:
        logger.exception("Unexpected error sending stats")
        await message.reply_text("Error al generar las estadísticas.")


@log_func
@authorized
async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lock command — remove inline keyboards from callup messages."""
    message = update.message
    if message is None:
        return
    settings: TelegramAppSettings = context.bot_data["settings"]
    container: Container = context.bot_data["container"]
    meetup = await _resolve_meetup(message, context.args, settings, container, "lock")
    if meetup is None:
        return
    await refresh_callup_messages(context.bot, settings, container, meetup, include_keyboard=False)
    await react_ok(context.bot, message)


@log_func
@authorized
async def unlock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unlock command — restore inline keyboards on callup messages."""
    message = update.message
    if message is None:
        return
    settings: TelegramAppSettings = context.bot_data["settings"]
    container: Container = context.bot_data["container"]
    meetup = await _resolve_meetup(message, context.args, settings, container, "unlock")
    if meetup is None:
        return
    await refresh_callup_messages(context.bot, settings, container, meetup)
    await react_ok(context.bot, message)


@log_func
@authorized
async def match_qr_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /match_qr command — send QR code of the match URL to each admin by DM."""
    message = update.message
    if message is None:
        return
    settings: TelegramAppSettings = context.bot_data["settings"]
    container: Container = context.bot_data["container"]
    if not settings.pyball.base_url:
        await message.reply_text("La URL base no está configurada.")
        return
    meetup = await _resolve_meetup(message, context.args, settings, container, "match_qr")
    if meetup is None:
        return
    try:
        url = container.start_match().execute(meetup.date)
    except MeetupHasNoTeamsError:
        display_date = format_display(meetup.date, settings.pyball.display_date_format)
        await message.reply_text(
            text=rf"El meetup del `{display_date}` no tiene equipos asignados\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    qr = generate_qr_bytes(url)
    for admin in settings.telegram.admins_ids:
        try:
            qr.seek(0)
            await context.bot.send_photo(
                chat_id=admin,
                photo=qr,
                caption=f"🔗 Enlace del partido:\n{url}",
            )
        except telegram.error.Forbidden:
            logger.error("Could not send message to '%s' admin", admin)
    await react_ok(context.bot, message)


@log_func
@authorized
async def change_location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_location [fecha hora] <nueva_localización> command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings: TelegramAppSettings = context.bot_data["settings"]
    args = context.args or []

    meetup_date, location_args = _try_parse_date_args(args, settings.pyball.display_date_format)
    new_location = " ".join(location_args).strip()

    if not new_location:
        await message.reply_text(
            _date_usage_msg(
                "change_location",
                settings.pyball.display_date_format,
                r"`<nueva_localización>`",
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if meetup_date is not None:
        meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            await message.reply_text("No existe ningún meetup para esa fecha.")
            return
    else:
        meetup = await _resolve_meetup(message, [], settings, container, "change_location")
        if meetup is None:
            return

    try:
        updated = container.update_meetup_location().execute(meetup.date, new_location)
        await refresh_callup_messages(context.bot, settings, container, updated)
        await react_ok(context.bot, message)
    except ValueError as error:
        await message.reply_text(str(error))
    except MeetupNotFoundError:
        await message.reply_text("No existe ningún meetup para esa fecha.")
    except Exception:
        logger.exception("Unexpected error changing meetup location")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def change_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_date [vieja_fecha vieja_hora] <nueva_fecha> <nueva_hora> command."""
    message = update.message
    if message is None:
        return

    settings: TelegramAppSettings = context.bot_data["settings"]
    args = context.args or []
    fmt = settings.pyball.display_date_format
    usage = _date_usage_msg(
        "change_date",
        fmt,
        r"`<nueva_fecha>` `<nueva_hora>`",
    )

    if len(args) not in (2, 4):
        await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return

    container: Container = context.bot_data["container"]
    dates = await _parse_change_date_args(args, message, settings, container)
    if dates is None:
        return
    old_date, new_date = dates

    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    try:
        updated = container.update_meetup_date().execute(old_date, new_date)
        store.rename_date(old_date, new_date)
        await refresh_callup_messages(context.bot, settings, container, updated)
        await react_ok(context.bot, message)
    except MeetupNotFoundError:
        await message.reply_text("No existe ningún meetup para esa fecha.")
    except ValueError as error:
        await message.reply_text(str(error))
    except DuplicateMeetupError:
        await message.reply_text("Ya existe un meetup en esa fecha.")
    except Exception:
        logger.exception("Unexpected error changing meetup date")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


def generate_qr_bytes(url: str) -> BytesIO:
    """Generate a PNG QR code for url and return it as a seeked BytesIO buffer."""
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf


async def _do_create_teams(
    meetup_date: datetime,
    container: Container,
    bot: telegram.Bot,
    settings: TelegramAppSettings,
    algo_name: str | None = None,
) -> Meetup:
    """Execute create_teams and refresh callup messages with updated keyboard."""
    meetup = container.create_teams(algo_name).execute(meetup_date)
    await refresh_callup_messages(bot, settings, container, meetup)
    return meetup


async def _create_meetup_and_send(
    date: datetime, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create meetup and send callup messages. Shared by new_meetup and next_meetup."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]
    settings: TelegramAppSettings = context.bot_data["settings"]

    date_str = format_display(date, settings.pyball.display_date_format)
    try:
        meetup = container.create_meetup().execute(date, settings.pyball.location)
    except DuplicateMeetupError:
        await message.reply_text(
            text=rf"Ya existe un meetup el `{date_str}`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    except Exception:
        logger.exception("Unexpected error creating meetup")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")
        return

    await _send_callup_messages(context, settings, container, meetup)
    await react_ok(context.bot, message)


async def _send_callup_messages(context, settings, container, meetup) -> None:
    """Send callup messages to regulars and substitutes chats."""
    player_repo = container.player_repository
    player_names = _get_player_names(player_repo)

    text = format_main_message(
        meetup,
        player_names,
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
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

        store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
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


async def _parse_manual_teams(
    message: Message,
    args: list[str],
    usage: str,
) -> tuple[list[str], list[str]] | None:
    """Parse team names from manual create_teams args. Returns None if invalid."""
    raw = " ".join(args[3:])
    parts = raw.split(";")
    team_a_names = [n.strip() for n in parts[0].split(",") if n.strip()]
    team_b_names = [n.strip() for n in parts[1].split(",") if n.strip()] if len(parts) > 1 else []
    if not team_a_names:
        await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
        return None
    return team_a_names, team_b_names


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


async def _parse_change_date_args(
    args: list[str],
    message: Message,
    settings: TelegramAppSettings,
    container: Container,
) -> tuple[datetime, datetime] | None:
    """Parse old and new dates from change_date args.

    Returns (old_date, new_date) or None if parsing failed or the meetup could not be resolved.
    """
    fmt = settings.pyball.display_date_format
    usage = _date_usage_msg("change_date", fmt, r"`<nueva_fecha>` `<nueva_hora>`")
    if len(args) == 2:
        old_meetup = await _resolve_meetup(message, [], settings, container, "change_date")
        if old_meetup is None:
            return None
        old_date = old_meetup.date
        try:
            new_date = parse_display(f"{args[0]} {args[1]}", fmt)
        except ValueError:
            await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
            return None
        return old_date, new_date
    if len(args) == 4:
        try:
            old_date = parse_display(f"{args[0]} {args[1]}", fmt)
        except ValueError:
            await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
            return None
        try:
            new_date = parse_display(f"{args[2]} {args[3]}", fmt)
        except ValueError:
            await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
            return None
        return old_date, new_date
    await message.reply_text(usage, parse_mode=ParseMode.MARKDOWN_V2)
    return None


def _try_parse_date_args(
    args: list[str], display_format: str
) -> tuple[datetime | None, list[str]]:
    """Parse the first two args as a date+time string if possible.

    Returns (parsed_date, remaining_args) on success, or (None, all_args) if the
    first two args do not form a valid date.
    """
    if len(args) >= 2:
        try:
            date = parse_display(f"{args[0]} {args[1]}", display_format)
            return date, args[2:]
        except ValueError:
            pass
    return None, list(args)


def _get_next_weekday(pyball_settings: PyballConfig) -> datetime:
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
