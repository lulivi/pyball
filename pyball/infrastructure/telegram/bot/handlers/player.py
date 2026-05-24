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

import functools
import locale
import logging

import telegram
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from pyball.exceptions import PlayerError
from pyball.infrastructure.telegram.bot.auth import authorized
from pyball.infrastructure.telegram.bot.reactions import react_ok
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.logger import log_func

logger = logging.getLogger(__name__)


def setup_player_handlers(application):
    """Register player-related handlers."""
    application.add_handler(CommandHandler("new_player", new_player_handler))
    application.add_handler(CommandHandler("rename_player", rename_player_handler))
    application.add_handler(CommandHandler("delete_player", delete_player_handler))
    application.add_handler(CommandHandler("list_players", list_players_handler))
    application.add_handler(CommandHandler("change_group", change_group_handler))
    application.add_handler(CommandHandler("link_player", link_player_handler))
    application.add_handler(CommandHandler("unlink_player", unlink_player_handler))


@log_func
@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text(
            text=r"Usage: `/new_player` `<name>` `<regular|substitute>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    name = args[0]
    group = args[1]

    if group not in ("regular", "substitute"):
        await message.reply_text(
            text=r"El grupo debe ser \`regular\` o \`substitute\`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        container.create_player().execute(name, group)
        await react_ok(context.bot, message)
    except PlayerAlreadyExistsError as error:
        await message.reply_text(
            text=rf"Ya existe un jugador con el nombre \`{error.name}\`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except PlayerError as error:
        logger.error("Player error creating player: %s", error)
        await message.reply_text("Error en el jugador. Inténtalo de nuevo.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error creating player: %s", error)
        await message.reply_text("Error de Telegram. Inténtalo de nuevo.")
    except Exception:
        logger.exception("Unexpected error creating player")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rename_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text(
            text=r"Usage: `/rename_player` `<player_id>` `<new_name>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_id = args[0]
    new_name = " ".join(args[1:])
    try:
        container.rename_player().execute(player_id, new_name)
        await react_ok(context.bot, message)
    except InvalidPlayerIdError:
        await message.reply_text("Formato de ID de jugador no válido.")
    except PlayerNotFoundError:
        await message.reply_text("Jugador no encontrado.")
    except NameAlreadyTakenError as error:
        await message.reply_text(
            text=rf"El nombre \`{error.name}\` ya está en uso por otro jugador\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except PlayerError as error:
        logger.error("Player error renaming player: %s", error)
        await message.reply_text("Error en el jugador. Inténtalo de nuevo.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error renaming player: %s", error)
        await message.reply_text("Error de Telegram. Inténtalo de nuevo.")
    except Exception:
        logger.exception("Unexpected error renaming player")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or not args:
        await message.reply_text(
            text=r"Usage: `/delete_player` `<player_id>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_id = args[0]
    try:
        container.delete_player().execute(player_id)
        await react_ok(context.bot, message)
    except InvalidPlayerIdError:
        await message.reply_text("Formato de ID de jugador no válido.")
    except PlayerNotFoundError:
        await message.reply_text("Jugador no encontrado.")
    except PlayerError as error:
        logger.error("Player error deleting player: %s", error)
        await message.reply_text("Error en el jugador. Inténtalo de nuevo.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error deleting player: %s", error)
        await message.reply_text("Error de Telegram. Inténtalo de nuevo.")
    except Exception:
        logger.exception("Unexpected error deleting player")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    players = container.player_repository.find_all()
    if not players:
        await message.reply_text("No hay jugadores registrados.")
        return

    regulares = []
    suplentes = []
    for p in players:
        if p.group == "regular":
            regulares.append(p.name)
        else:
            suplentes.append(p.name)

    sorted_regulars = sorted(regulares, key=functools.cmp_to_key(locale.strcoll))
    sorted_substitutes = sorted(suplentes, key=functools.cmp_to_key(locale.strcoll))

    lines = ["*Jugadores:*", ""]
    if sorted_regulars:
        lines.append(rf"*Titulares \({len(sorted_regulars)}\):*")
        for name in sorted_regulars:
            lines.append(rf"\- `{name}`")
    if sorted_substitutes:
        lines.append(rf"*Suplentes \({len(sorted_substitutes)}\):*")
        for name in sorted_substitutes:
            lines.append(rf"\- `{name}`")

    await message.reply_text(
        text="\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@log_func
@authorized
async def change_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_group command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text(
            text=r"Usage: `/change_group` `<player_name>` `<regular|substitute>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_name = args[0]
    new_group = args[1]

    if new_group not in ("regular", "substitute"):
        await message.reply_text("El grupo debe ser 'regular' o 'substitute'.")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    try:
        use_case = container.change_player_group()
        use_case.execute(str(match.player_id.value), new_group)
        await react_ok(context.bot, message)
    except telegram.error.TelegramError as error:
        logger.error("Telegram error changing player group: %s", error)
        await message.reply_text("Error de Telegram al cambiar el grupo.")
    except PlayerError as error:
        logger.error("Player error changing group: %s", error)
        await message.reply_text("Error al cambiar el grupo del jugador.")
    except Exception:
        logger.exception("Unexpected error changing player group")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


@log_func
@authorized
async def link_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /link_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text(
            text=r"Usage: `/link_player` `<player_name>` `<telegram_id>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_name = args[0]
    try:
        telegram_id = int(args[1])
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
                "Elimina el enlace primero con /unlink_player <telegram_id>"
            )
        return

    mapping_store.set_player_id(telegram_id, player_id_str)

    await react_ok(context.bot, message)


@log_func
@authorized
async def unlink_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unlink_player command."""
    message = update.message
    if message is None:
        return

    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")

    args = context.args
    if args is None or not args:
        await message.reply_text(
            text=r"Usage: `/unlink_player `<telegram_id>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.reply_text("ID de Telegram no válido. Debe ser un número.")
        return

    player_id = mapping_store.get_player_id(telegram_id)
    if not player_id:
        await message.reply_text("Este ID de Telegram no está vinculado a ningún jugador.")
        return

    mapping_store.delete_player_id(telegram_id)
    await react_ok(context.bot, message)
