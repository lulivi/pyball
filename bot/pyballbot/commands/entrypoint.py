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

import logging
import sys

from telegram.ext import Application, CommandHandler, MessageHandler

from pyballbot.commands.error_handler import command_error
from pyballbot.commands.filters import ALLOWED_CHATS_FILTER
from pyballbot.commands.help import command_help
from pyballbot.commands.meetup.entrypoint import add_meetup_handlers
from pyballbot.commands.player.entrypoint import add_player_handlers
from pyballbot.commands.start import command_start
from pyballbot.commands.version import command_version
from pyballbot.commands.wrong_chat import wrong_chat
from pyballbot.settings import BOT_TOKEN

logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and build the bot application.

    :returns: The built application.

    """
    if not BOT_TOKEN:
        sys.exit("`BOT_TOKEN` environment variable is needed to run the application")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        CommandHandler(
            command=("h", "help"),
            callback=command_help,
            filters=ALLOWED_CHATS_FILTER,
        )
    )
    application.add_handler(
        CommandHandler(
            command="start",
            callback=command_start,
            filters=ALLOWED_CHATS_FILTER,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("v", "version"),
            callback=command_version,
            filters=ALLOWED_CHATS_FILTER,
        )
    )

    # Player
    add_player_handlers(application=application)

    # Meetup
    add_meetup_handlers(application=application)

    # Errors
    application.add_handler(
        MessageHandler(
            callback=wrong_chat,
            filters=~ALLOWED_CHATS_FILTER,
        )
    )
    application.add_error_handler(command_error)

    return application
