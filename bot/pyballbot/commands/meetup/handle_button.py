import datetime
import logging
import uuid

from pyballbot.requests.errors import PlayerIsAreadyCalled
from telegram import Update
from telegram.ext import ContextTypes

from pyballbot import player_telegram_id_translator as translator
from pyballbot.commands.utils import (
    get_meetup_date_time_from_message,
    send_message_to_admins,
    update_meetup_messages,
)
from pyballbot.logger import log_func
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests.types import Meetup

logger = logging.getLogger(__name__)


@log_func
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query is None or query.message is None:
        return

    logger.info("Handling join/leave button")

    try:
        player_id: (
            uuid.UUID
        ) = translator.PlayerToTelegramIdTranslatorService().translate_telegram_id(
            telegram_id=str(update.effective_user.id)
        )
    except translator.PlayerTelegramIdNotFound as error:
        await send_message_to_admins(
            message_function=context.bot.send_message,
            text=(
                "The player that pressed the button"
                f" {update.effective_user.full_name} ({update.effective_user.id}) has no player"
                " associated. Please, create a new player ask the them to retry."
            ),
        )
        await query.answer("Please, contact an administrator")
        return

    meetup_date_time: datetime.datetime = get_meetup_date_time_from_message(query.message.text)

    meetup: Meetup = meetup_requests.get_by(date_time=meetup_date_time)

    query_answer = "Nothing has been done."

    logger.warning(f"Meetup players: {meetup.players}")
    logger.warning(f"Player ID: {player_id}")

    try:
        logger.debug(f"Trying to add player {player_id} to meetup {meetup.id}")
        meetup_requests.add_player(meetup_id=meetup.id, player_id=player_id)
        query_answer = "You have been ADDED to the meetup"
    except PlayerIsAreadyCalled:
        logger.debug(f"The player is already in the meetup, removing player {player_id}")
        meetup_requests.remove_player(meetup_id=meetup.id, player_id=player_id)
        query_answer = "You have been REMOVED from the meetup"
    finally:
        await query.answer(query_answer)

    # TODO: event?
    await update_meetup_messages(
        meetup_id=meetup.id,
        send_message_func=context.bot.send_message,
        edit_message_func=context.bot.edit_message_text,
    )
