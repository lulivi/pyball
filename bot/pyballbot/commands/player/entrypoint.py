from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

from pyballbot.commands.filters import ADMIN_USERS_FILTER, BASE_CONVERSATIONS_FILTER
from pyballbot.commands.player import create, rename


def add_player_handlers(application: Application) -> None:
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "player_create",
                    create.ask_player_name,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                create.CreatePlayerState.ENTER_PLAYER_TELEGRAM_ID: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=create.save_player_name_ask_telegram_id,
                    )
                ],
                create.CreatePlayerState.ENTER_PLAYER_ROLE: [
                    MessageHandler(
                        filters=filters.Regex(r"\d+") & BASE_CONVERSATIONS_FILTER,
                        callback=create.save_telegram_id_ask_role,
                    )
                ],
                create.CreatePlayerState.SAVE_PLAYER: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=create.save_player,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", create.cancel_player_creation)],
        )
    )
    application.add_handler(
        ConversationHandler(
            entry_points=[
                CommandHandler(
                    "player_rename",
                    rename.ask_player_name,
                    filters=ADMIN_USERS_FILTER,
                )
            ],
            states={
                rename.RenamePlayerState.ASK_NEW_PLAYER_NAME: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=rename.save_current_name_ask_new_name,
                    )
                ],
                rename.RenamePlayerState.UPDATE_PLAYER: [
                    MessageHandler(
                        filters=filters.TEXT & BASE_CONVERSATIONS_FILTER,
                        callback=rename.rename_player,
                    )
                ],
            },
            fallbacks=[CommandHandler("cancel", rename.cancel_player_renaming)],
        )
    )
