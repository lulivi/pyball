# Copyright (c) 2022 Luis Liñán
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

"""Bot to help organize game call-ups."""

import locale
import logging

import peewee

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from pyball.legacy.bot.commands import (
    button_game,
    command_callup,
    command_error,
    command_match,
    command_player,
    command_version,
    message_from_wrong_chat,
)
from pyball.legacy.db.errors import PyBallDbError
from pyball.legacy.db.model import database
from pyball.legacy.db.utils import get_player_id_list
from pyball.settings import ADMINS_IDS, BOT_TOKEN, DATABASE_FILE_PATH, LOCALE, REGULARS_ID

# Set locale for sorting player names
locale.setlocale(locale.LC_ALL, LOCALE)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and build the bot application.

    :returns: The built application.

    """
    database.initialize(peewee.SqliteDatabase(DATABASE_FILE_PATH))
    logger.debug(f"Using database file {DATABASE_FILE_PATH}")

    allowed_chat_ids: set = {REGULARS_ID, *ADMINS_IDS}
    try:
        allowed_chat_ids |= set(get_player_id_list())
    except PyBallDbError as error:
        logger.error(f"Error getting the player id list from `{DATABASE_FILE_PATH}`: {error}")
    included_chats_filter = filters.Chat(allowed_chat_ids)
    update_filters = ~filters.UpdateType.EDITED_MESSAGE & included_chats_filter

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(
        CommandHandler(
            command=("start", "help"),
            callback=message_from_wrong_chat,
            filters=update_filters,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("v", "version"),
            callback=command_version,
            filters=update_filters,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("m", "match"),
            callback=command_match,
            filters=update_filters,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("p", "player"),
            callback=command_player,
            filters=update_filters,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("c", "callup"),
            callback=command_callup,
            filters=update_filters,
        )
    )
    application.add_handler(CallbackQueryHandler(button_game))
    application.add_handler(
        MessageHandler(
            callback=message_from_wrong_chat,
            filters=~included_chats_filter,
        )
    )
    application.add_error_handler(command_error)

    return application
