"""Player command handlers."""

import functools
import html
import locale
import logging

import telegram
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from pyball.application.container import Container
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.bot.auth import authorized
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from pyball.exceptions import PlayerError
from pyball.infrastructure.telegram.mapping import TelegramMappingStore

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

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
            r"Usage: `/new_player` `<name>` `<regular|substitute>`", parse_mode="MarkdownV2"
        )
        return

    name = args[0]
    group = args[1]

    if group not in ("regular", "substitute"):
        await message.reply_text("Group must be 'regular' or 'substitute'")
        return

    try:
        player = container.create_player().execute(name, group)
        await message.reply_text(
            rf"Player `{player.name}` created as {group}\!", parse_mode="MarkdownV2"
        )
    except PlayerAlreadyExistsError as error:
        await message.reply_text(html.escape(str(error)), parse_mode="HTML")
    except PlayerError as error:
        logger.error("Player error creating player: %s", error)
        await message.reply_text("Player error. Please try again.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error creating player: %s", error)
        await message.reply_text("Telegram error. Please try again.")
    except Exception as error:
        logger.exception("Error creating player: %s", error)
        await message.reply_text("An error occurred. Please contact an admin.")


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
            r"Usage: `/rename_player` `<player_id>` `<new_name>`", parse_mode="MarkdownV2"
        )
        return

    player_id = args[0]
    new_name = " ".join(args[1:])
    try:
        player = container.rename_player().execute(player_id, new_name)
        await message.reply_text(rf"Player renamed to `{player.name}`\!", parse_mode="MarkdownV2")
    except InvalidPlayerIdError:
        await message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await message.reply_text("Player not found.")
    except NameAlreadyTakenError as error:
        await message.reply_text(html.escape(str(error)), parse_mode="HTML")
    except PlayerError as error:
        logger.error("Player error renaming player: %s", error)
        await message.reply_text("Player error. Please try again.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error renaming player: %s", error)
        await message.reply_text("Telegram error. Please try again.")
    except Exception as error:
        logger.exception("Error renaming player: %s", error)
        await message.reply_text("An error occurred. Please contact an admin.")


@authorized
async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    args = context.args
    if args is None or not args:
        await message.reply_text(r"Usage: `/delete_player` `<player_id>`", parse_mode="MarkdownV2")
        return

    player_id = args[0]
    try:
        container.delete_player().execute(player_id)
        await message.reply_text("Player deleted!")
    except InvalidPlayerIdError:
        await message.reply_text("Invalid player ID format.")
    except PlayerNotFoundError:
        await message.reply_text("Player not found.")
    except PlayerError as error:
        logger.error("Player error deleting player: %s", error)
        await message.reply_text("Player error. Please try again.")
    except telegram.error.TelegramError as error:
        logger.error("Telegram error deleting player: %s", error)
        await message.reply_text("Telegram error. Please try again.")
    except Exception as error:
        logger.exception("Error deleting player: %s", error)
        await message.reply_text("An error occurred. Please contact an admin.")


@authorized
async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    players = container.player_repository.find_all()
    if not players:
        await message.reply_text("No players found.")
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

    await message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


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
            r"Usage: `/change_group` `<player_name>` `<regular|substitute>`",
            parse_mode="MarkdownV2",
        )
        return

    player_name = args[0]
    new_group = args[1]

    if new_group not in ("regular", "substitute"):
        await message.reply_text("Group must be 'regular' or 'substitute'")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError as error:
        await message.reply_text(str(error))
        return

    try:
        use_case = container.change_player_group()
        player = use_case.execute(str(match.player_id.value), new_group)
        await message.reply_text(
            rf"Player `{player.name}` changed to `{new_group}`\!", parse_mode="MarkdownV2"
        )
    except telegram.error.TelegramError as error:
        logger.error("Telegram error changing player group: %s", error)
        await message.reply_text("Telegram error. Failed to change group.")
    except PlayerError as error:
        logger.error("Player error changing group: %s", error)
        await message.reply_text("Player error. Failed to change group.")
    except Exception as error:
        logger.exception("Error changing player group: %s", error)
        await message.reply_text("Error changing player group.")


@authorized
async def link_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /link_player command."""
    message = update.message
    if message is None:
        return

    container: Container = context.bot_data["container"]

    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.bot_mappings_file)

    args = context.args
    if args is None or len(args) < 2:
        await message.reply_text(
            r"Usage: `/link_player` `<player_name>` `<telegram_id>`", parse_mode="MarkdownV2"
        )
        return

    player_name = args[0]
    try:
        telegram_id = int(args[1])
    except ValueError:
        await message.reply_text("Invalid telegram_id. Must be a number.")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()

    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError as error:
        await message.reply_text(html.escape(str(error)), parse_mode="HTML")
        return

    player_id_str = str(match.player_id.value)

    existing_telegram_id = mapping_store.get_player_id(telegram_id)
    if existing_telegram_id:
        if existing_telegram_id == player_id_str:
            await message.reply_text("This Telegram ID is already linked to this player.")
        else:
            await message.reply_text(
                (
                    "This Telegram ID is already linked to another player. "
                    "Remove the link first with /unlink_player <telegram_id>"
                ),
                parse_mode="HTML",
            )
        return

    mapping_store.set_player_id(telegram_id, player_id_str)

    await message.reply_text(
        rf"Telegram ID `{telegram_id}` linked to player `{match.name}`\!", parse_mode="MarkdownV2"
    )


@authorized
async def unlink_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unlink_player command."""
    message = update.message
    if message is None:
        return

    settings = context.bot_data["settings"]
    mapping_store = TelegramMappingStore(settings.paths.bot_mappings_file)

    args = context.args
    if args is None or not args:
        await message.reply_text(
            r"Usage: `/unlink_player `<telegram_id>`", parse_mode="MarkdownV2"
        )
        return

    try:
        telegram_id = int(args[0])
    except ValueError:
        await message.reply_text("Invalid telegram_id. Must be a number.")
        return

    player_id = mapping_store.get_player_id(telegram_id)
    if not player_id:
        await message.reply_text("This Telegram ID is not linked to any player.")
        return

    mapping_store.delete_player_id(telegram_id)
    await message.reply_text(
        rf"Link for Telegram ID `{telegram_id}` removed\!", parse_mode="MarkdownV2"
    )
