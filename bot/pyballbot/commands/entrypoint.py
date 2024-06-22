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
import sys

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pyball.greenfield.utils.bot.commands import meetup_add_player, meetup_create, player_create
from pyball.greenfield.utils.bot.commands.error_handler import command_error
from pyball.greenfield.utils.bot.commands.help import command_help
from pyball.greenfield.utils.bot.commands.version import command_version
from pyball.greenfield.utils.bot.commands.wrong_chat import wrong_chat
from pyball.greenfield.utils.bot.utils import enum_as_regex
from pyball.legacy.bot.commands import button_game
from pyball.settings import ADMINS_IDS, BOT_TOKEN, LOCALE, REGULARS_ID

# Set locale for sorting player names
locale.setlocale(locale.LC_ALL, LOCALE)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and build the bot application.

    :returns: The built application.

    """
    if not BOT_TOKEN:
        sys.exit("`BOT_TOKEN` environment variable is needed to run the application")

    filter_admin_users = ~filters.UpdateType.EDITED_MESSAGE & filters.User(ADMINS_IDS)
    filter_allowed_chats = ~filters.UpdateType.EDITED_MESSAGE & filters.Chat(
        {*ADMINS_IDS, REGULARS_ID}
    )  # Add all main players ids and
    filters_base_conversations = ~filters.COMMAND & filter_admin_users

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(
        CommandHandler(
            command=("h", "help", "start"),
            callback=command_help,
            filters=filter_allowed_chats,
        )
    )
    application.add_handler(
        CommandHandler(
            command=("v", "version"),
            callback=command_version,
            filters=filter_allowed_chats,
        )
    )

    # Player
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "player_create", player_create.ask_player_name, filters=filter_admin_users
                )
            ],
            states={
                player_create.CreatePlayerState.ENTER_PLAYER_TELEGRAM_ID: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=player_create.save_player_name_ask_telegram_id,
                    )
                ],
                player_create.CreatePlayerState.SAVE_PLAYER: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+") & filters_base_conversations,
                        callback=player_create.save_player,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", player_create.cancel_player_creation)],
        )
    )

    # Meetup
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_create", meetup_create.ask_date_time, filters=filter_admin_users
                )
            ],
            states={
                meetup_create.CreateMeetupState.SELECT_LOCATION: [
                    MessageHandler(
                        filters=(
                            filters.Regex(
                                f"^({enum_as_regex(meetup_create.NewMeetupDateTime)}|\d{{1,2}}\/[a-zA-Z]{{3}}\/\d{{4}}"
                                " \d{2}\:\d{2})$"
                            )
                            & filters_base_conversations
                        ),
                        callback=meetup_create.save_date_time_ask_location,
                    )
                ],
                meetup_create.CreateMeetupState.SELECT_TEAM_SIZES: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_create.save_location_ask_team_sizes,
                    )
                ],
                meetup_create.CreateMeetupState.SAVE_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+(,\s?\d+)*") & filters_base_conversations,
                        callback=meetup_create.save_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", meetup_create.cancel_meetup_creation)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_add_player",
                    meetup_add_player.ask_meetup_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_add_player.AddPlayerToMeetupState.ASK_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_add_player.save_meetup_date_time_ask_player_name,
                    )
                ],
                meetup_add_player.AddPlayerToMeetupState.ADD_PLAYER_TO_MEETUP: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_add_player.add_player_to_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", meetup_add_player.cancel_player_addition)],
        )
    )
    # application.add_handler(CallbackQueryHandler(button_game))

    # Errors
    application.add_handler(
        MessageHandler(
            callback=wrong_chat,
            filters=~filter_allowed_chats,
        )
    )
    application.add_error_handler(command_error)

    return application
