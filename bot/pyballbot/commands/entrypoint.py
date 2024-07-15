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

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pyballbot.commands import meetup as meetup_commands
from pyballbot.commands import player as player_commands
from pyballbot.commands.error_handler import command_error
from pyballbot.commands.help import command_help
from pyballbot.commands.utils import INLINE_KEYBOARD_JOIN_LEAVE_MEETUP
from pyballbot.commands.version import command_version
from pyballbot.commands.wrong_chat import wrong_chat
from pyballbot.settings import ADMINS_IDS, BOT_TOKEN, DISPLAY_DATE_FORMAT_PATTERN, REGULARS_ID
from pyballbot.utils import enum_as_regex

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
    )  # Add all main players ids and admins
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
                    "player_create",
                    player_commands.create.ask_player_name,
                    filters=filter_admin_users,
                )
            ],
            states={
                player_commands.create.CreatePlayerState.ENTER_PLAYER_TELEGRAM_ID: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=player_commands.create.save_player_name_ask_telegram_id,
                    )
                ],
                player_commands.create.CreatePlayerState.ENTER_PLAYER_ROLE: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+") & filters_base_conversations,
                        callback=player_commands.create.save_telegram_id_ask_role,
                    )
                ],
                player_commands.create.CreatePlayerState.SAVE_PLAYER: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=player_commands.create.save_player,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", player_commands.create.cancel_player_creation)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "player_rename",
                    player_commands.rename.ask_player_name,
                    filters=filter_admin_users,
                )
            ],
            states={
                player_commands.rename.RenamePlayerState.ASK_NEW_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=player_commands.rename.save_current_name_ask_new_name,
                    )
                ],
                player_commands.rename.RenamePlayerState.UPDATE_PLAYER: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=player_commands.rename.rename_player,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", player_commands.rename.cancel_player_renaming)],
        )
    )

    # Meetup
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_create",
                    meetup_commands.create.ask_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_commands.create.CreateMeetupState.SELECT_LOCATION: [
                    MessageHandler(
                        filters=(
                            filters.Regex(
                                f"^({enum_as_regex(meetup_commands.create.NewMeetupDateTime)}|"
                                f"{DISPLAY_DATE_FORMAT_PATTERN})$"
                            )
                            & filters_base_conversations
                        ),
                        callback=meetup_commands.create.save_date_time_ask_location,
                    )
                ],
                meetup_commands.create.CreateMeetupState.SELECT_TEAM_SIZES: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_commands.create.save_location_ask_team_sizes,
                    )
                ],
                meetup_commands.create.CreateMeetupState.SAVE_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+(,\s?\d+)*") & filters_base_conversations,
                        callback=meetup_commands.create.save_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", meetup_commands.create.cancel_meetup_creation)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_display",
                    meetup_commands.display.ask_meetup_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_commands.display.DisplayMeetupState.DISPLAY_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & filters_base_conversations,
                        callback=meetup_commands.display.display_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", meetup_commands.display.cancel_meetup_display)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_add_player",
                    meetup_commands.add_player.ask_meetup_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_commands.add_player.AddPlayerToMeetupState.ASK_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & filters_base_conversations,
                        callback=meetup_commands.add_player.save_meetup_date_time_ask_player_name,
                    )
                ],
                meetup_commands.add_player.AddPlayerToMeetupState.ADD_PLAYER_TO_MEETUP: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_commands.add_player.add_player_to_meetup,
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", meetup_commands.add_player.cancel_player_addition)
            ],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_remove_player",
                    meetup_commands.remove_player.ask_meetup_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_commands.remove_player.RemovePlayerFromMeetupState.ASK_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & filters_base_conversations,
                        callback=meetup_commands.remove_player.save_meetup_date_time_ask_player_name,
                    )
                ],
                meetup_commands.remove_player.RemovePlayerFromMeetupState.REMOVE_PLAYER_FROM_MEETUP: [
                    MessageHandler(
                        filters=filters.TEXT & filters_base_conversations,
                        callback=meetup_commands.remove_player.remove_player_from_meetup,
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", meetup_commands.remove_player.cancel_player_removal)
            ],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_search_substitutes",
                    meetup_commands.search_substitutes.ask_meetup_date_time,
                    filters=filter_admin_users,
                )
            ],
            states={
                meetup_commands.search_substitutes.SearchSubstitutesState.DISPLAY_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & filters_base_conversations,
                        callback=meetup_commands.search_substitutes.send_search,
                    )
                ],
            },
            fallbacks=[
                CommandHandler("cancel", meetup_commands.search_substitutes.cancel_meetup_search)
            ],
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            meetup_commands.handle_join_leave_button.handle,
            pattern=INLINE_KEYBOARD_JOIN_LEAVE_MEETUP,
        )
    )

    # Errors
    application.add_handler(
        MessageHandler(
            callback=wrong_chat,
            filters=~filter_allowed_chats,
        )
    )
    application.add_error_handler(command_error)

    return application
