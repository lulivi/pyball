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

import peewee

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, PicklePersistence
from telegram.ext.filters import UpdateType

from pyball.bot.commands import (
    button_game,
    command_callup,
    command_help,
    command_match,
    command_player,
)
from pyball.db.model import database
from pyball.settings import BOT_TOKEN, DATABASE_FILE_PATH, LOCALE, PERSISTENCE_FILE_PATH

# Set locale for sorting player names
locale.setlocale(locale.LC_ALL, LOCALE)


def build_application() -> Application:
    """Create and build the bot application.

    :returns: The built application.

    """
    my_persistence = PicklePersistence(filepath=PERSISTENCE_FILE_PATH)
    database.initialize(peewee.SqliteDatabase(DATABASE_FILE_PATH))

    application = Application.builder().token(BOT_TOKEN).persistence(my_persistence).build()
    application.add_handler(
        CommandHandler(("start", "help"), command_help, ~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(
        CommandHandler(("m", "match"), command_match, ~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(
        CommandHandler(("p", "player"), command_player, ~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(
        CommandHandler(("c", "callup"), command_callup, ~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(CallbackQueryHandler(button_game))

    return application
