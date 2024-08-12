from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from pyballbot.commands.filters import ADMIN_USERS_FILTER, BASE_CONVERSATIONS_FILTER
from pyballbot.commands.meetup import (
    add_player,
    create,
    display,
    handle_join_leave_button,
    remove_player,
    search_substitutes,
)
from pyballbot.commands.utils import INLINE_KEYBOARD_JOIN_LEAVE_MEETUP
from pyballbot.settings import DISPLAY_DATE_FORMAT_PATTERN
from pyballbot.utils import enum_as_regex


def add_meetup_handlers(application: Application) -> None:
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_create",
                    create.ask_date_time,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                create.CreateMeetupState.SELECT_LOCATION: [
                    MessageHandler(
                        filters=(
                            filters.Regex(
                                f"^({enum_as_regex(create.NewMeetupDateTime)}|"
                                f"{DISPLAY_DATE_FORMAT_PATTERN})$"
                            )
                            & BASE_CONVERSATIONS_FILTER
                        ),
                        callback=create.save_date_time_ask_location,
                    )
                ],
                create.CreateMeetupState.SELECT_TEAM_SIZES: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=create.save_location_ask_team_sizes,
                    )
                ],
                create.CreateMeetupState.SAVE_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+(,\s?\d+)*") & BASE_CONVERSATIONS_FILTER,
                        callback=create.save_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", create.cancel_meetup_creation)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_display",
                    display.ask_meetup_date_time,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                display.DisplayMeetupState.DISPLAY_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & BASE_CONVERSATIONS_FILTER,
                        callback=display.display_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", display.cancel_meetup_display)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_add_player",
                    add_player.ask_meetup_date_time,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                add_player.AddPlayerToMeetupState.ASK_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & BASE_CONVERSATIONS_FILTER,
                        callback=add_player.save_meetup_date_time_ask_player_name,
                    )
                ],
                add_player.AddPlayerToMeetupState.ADD_PLAYER_TO_MEETUP: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=add_player.add_player_to_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", add_player.cancel_player_addition)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_remove_player",
                    remove_player.ask_meetup_date_time,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                remove_player.RemovePlayerFromMeetupState.ASK_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & BASE_CONVERSATIONS_FILTER,
                        callback=remove_player.save_meetup_date_time_ask_player_name,
                    )
                ],
                remove_player.RemovePlayerFromMeetupState.REMOVE_PLAYER_FROM_MEETUP: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=remove_player.remove_player_from_meetup,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", remove_player.cancel_player_removal)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "meetup_search_substitutes",
                    search_substitutes.ask_meetup_date_time,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                search_substitutes.SearchSubstitutesState.DISPLAY_MEETUP: [
                    MessageHandler(
                        filters=filters.Regex(DISPLAY_DATE_FORMAT_PATTERN)
                        & BASE_CONVERSATIONS_FILTER,
                        callback=search_substitutes.send_search,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", search_substitutes.cancel_meetup_search)],
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_join_leave_button.handle,
            pattern=INLINE_KEYBOARD_JOIN_LEAVE_MEETUP,
        )
    )
