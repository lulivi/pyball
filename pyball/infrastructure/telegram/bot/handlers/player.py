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
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.player.errors import NameAlreadyTakenError, PlayerAlreadyExistsError
from pyball.domain.player.models import VALID_POSITIONS
from pyball.exceptions import PlayerError
from pyball.infrastructure.telegram.bot.auth import authorized
from pyball.infrastructure.telegram.bot.handlers.general import add_command
from pyball.infrastructure.telegram.bot.reactions import react_ok
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.logger import log_func

logger = logging.getLogger(__name__)


def setup_player_handlers(application):
    """Register player-related handlers."""
    add_command(application, "player_new", new_player_handler)
    add_command(application, "player_rename", rename_player_handler)
    add_command(application, "player_delete", delete_player_handler)
    add_command(application, "player_list", list_players_handler)
    add_command(application, "player_change_group", change_group_handler)
    add_command(application, "player_change_position", change_position_handler)
    add_command(application, "player_link", link_player_handler)
    add_command(application, "player_unlink", unlink_player_handler)


@log_func
@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_new command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    parts = [p.strip() for p in " ".join(context.args or []).split(",")]
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        await message.reply_text(
            text=r"Usage: `/player_new` `<name>, <regular|substitute>[, <posición>]`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    name, group = parts[0], parts[1]
    position = parts[2] if len(parts) == 3 and parts[2] else None

    if group not in ("regular", "substitute"):
        await message.reply_text(
            text=r"El grupo debe ser \`regular\` o \`substitute\`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if position is not None and position not in VALID_POSITIONS:
        await message.reply_text(
            f"Posición no válida. Debe ser una de: {', '.join(VALID_POSITIONS)}."
        )
        return

    try:
        container.create_player().execute(name, group, position)
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
    """Handle /player_rename command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    # Names may contain spaces, so old and new name are separated by a comma.
    player_name, _, new_name = " ".join(context.args or []).partition(",")
    player_name = player_name.strip()
    new_name = new_name.strip()
    if not player_name or not new_name:
        await message.reply_text(
            text=r"Usage: `/player_rename` `<old_name>, <new_name>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_repo = container.player_repository
    try:
        match = fuzzy_match_player(player_name, player_repo.find_all())
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    try:
        container.rename_player().execute(str(match.player_id.value), new_name)
        await react_ok(context.bot, message)
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
    """Handle /player_delete command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    player_name = " ".join(context.args or []).strip()
    if not player_name:
        await message.reply_text(
            text=r"Usage: `/player_delete` `<player_name>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    player_repo = container.player_repository
    try:
        match = fuzzy_match_player(player_name, player_repo.find_all())
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    try:
        container.delete_player().execute(str(match.player_id.value))
        await react_ok(context.bot, message)
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
    """Handle /player_list command."""
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
        label = rf"\- `{p.name}`" + (rf" _{p.position}_" if p.position else "")
        if p.group == "regular":
            regulares.append((p.name, label))
        else:
            suplentes.append((p.name, label))

    sorted_regulars = sorted(regulares, key=lambda t: functools.cmp_to_key(locale.strcoll)(t[0]))
    sorted_substitutes = sorted(
        suplentes, key=lambda t: functools.cmp_to_key(locale.strcoll)(t[0])
    )

    lines = ["*Jugadores:*", ""]
    if sorted_regulars:
        lines.append(rf"*Titulares \({len(sorted_regulars)}\):*")
        lines.extend(label for _, label in sorted_regulars)
    if sorted_substitutes:
        lines.append(rf"*Suplentes \({len(sorted_substitutes)}\):*")
        lines.extend(label for _, label in sorted_substitutes)

    await message.reply_text(
        text="\n".join(lines),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@log_func
@authorized
async def change_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_change_group command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    player_name, _, new_group = " ".join(context.args or []).partition(",")
    player_name = player_name.strip()
    new_group = new_group.strip()
    if not player_name or not new_group:
        await message.reply_text(
            text=r"Usage: `/player_change_group` `<player_name>, <regular|substitute>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

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
async def change_position_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /player_change_position command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    player_name, _, new_position_raw = " ".join(context.args or []).partition(",")
    player_name = player_name.strip()
    new_position_raw = new_position_raw.strip().lower()
    if not player_name or not new_position_raw:
        await message.reply_text(
            text=r"Usage: `/player_change_position` `<player_name>, <posición|ninguna>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    new_position = None if new_position_raw == "ninguna" else new_position_raw
    if new_position is not None and new_position not in VALID_POSITIONS:
        await message.reply_text(
            f"Posición no válida. Debe ser una de: {', '.join(VALID_POSITIONS)}, o 'ninguna'."
        )
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError:
        await message.reply_text("No se encontró ningún jugador con ese nombre.")
        return

    try:
        container.set_player_position().execute(str(match.player_id.value), new_position)
        await react_ok(context.bot, message)
    except telegram.error.TelegramError as error:
        logger.error("Telegram error changing player position: %s", error)
        await message.reply_text("Error de Telegram al cambiar la posición.")
    except PlayerError as error:
        logger.error("Player error changing position: %s", error)
        await message.reply_text("Error al cambiar la posición del jugador.")
    except Exception:
        logger.exception("Unexpected error changing player position")
        await message.reply_text("Ha ocurrido un error inesperado. Contacta con el administrador.")


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
