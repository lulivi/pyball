import datetime
import logging
import uuid

from typing import Callable, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden
from telegram.ext import ExtBot

from pyballbot.meetup_to_telegram_id_translator import (
    MeetupIdNotFound,
    MeetupMessagesIds,
    MeetupToTelegramIdTranslator,
)
from pyballbot.requests import meetup as meetup_requests
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.requests.types import DisplayMeetup
from pyballbot.settings import ADMINS_IDS, DISPLAY_DATETIME_FORMAT, REGULARS_ID, SUBSTITUTES_ID
from pyballbot.utils import bot_call_message_function

logger = logging.getLogger(__name__)

INLINE_KEYBOARD_JOIN_LEAVE_MEETUP = "join/leave"

MEETUP_TELEGRAM_INLINE_KEYBOARD: InlineKeyboardMarkup = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Apuntarme / Desapuntarme", callback_data=INLINE_KEYBOARD_JOIN_LEAVE_MEETUP
            )
        ]
    ]
)


async def send_message_to_admins(message_function, text: str) -> None:
    for admin_id in ADMINS_IDS:
        await bot_call_message_function(
            message_function=message_function,
            text=text,
            chat_id=admin_id,
        )


def get_meetup_date_time_from_message(text: str) -> datetime.datetime:
    """Parse the datetime from the Meetup message.

    Get the date time string from the first line of the message which format is:

    ..code::

        Fecha: day DD/mmm/YYYY HH:MM

    Example:

    ..code::

        Fecha: Monday 10/Jun/2024 20:00
    """
    return datetime.datetime.strptime(
        text.splitlines()[0].split(maxsplit=1)[-1].strip(), DISPLAY_DATETIME_FORMAT
    )


async def update_meetup_messages(
    meetup_id: uuid.UUID,
    send_message_func: Callable,
    edit_message_func: Callable,
) -> None:
    try:
        message_ids: MeetupMessagesIds = MeetupToTelegramIdTranslator().get(meetup_id=meetup_id)
    except MeetupIdNotFound:
        logger.debug(f"No meetup message found for meetup `{meetup_id}`")
        return

    try:
        display_meetup: DisplayMeetup = meetup_requests.get_display_meetup(
            id=meetup_id,
        )
    except CouldNotConnectToTheCore as error:
        await send_message_to_admins(
            message_function=send_message_func,
            text=(
                f"There is a problem contacting Pyball core when updating meetup message: {error}"
            ),
        )
        return

    meetup_date_time_string = display_meetup.date_time.strftime(DISPLAY_DATETIME_FORMAT)

    try:
        logger.info(f"Updating regulars chat display meetup {meetup_date_time_string}")
        await bot_call_message_function(
            message_function=edit_message_func,
            text=display_meetup.to_string(),
            chat_id=REGULARS_ID,
            message_id=message_ids.regulars_id,
            reply_markup=MEETUP_TELEGRAM_INLINE_KEYBOARD,
        )
    except BadRequest as error:
        error_message = parse_update_request_error(
            meetup_date_time_string=meetup_date_time_string,
            error=error,
        )
        if "Deleting the saved reference" in error_message:
            MeetupToTelegramIdTranslator().delete(meetup_id=meetup_id)
        await send_message_to_admins(message_function=send_message_func, text=error_message)

    try:
        message_ids: MeetupMessagesIds = MeetupToTelegramIdTranslator().get(meetup_id=meetup_id)
    except MeetupIdNotFound:
        logger.debug(
            f"The meetup message was not found and the reference was deleted: `{meetup_id}`"
        )
        return

    if message_ids.substitutes_id is not None:
        try:
            logger.info(f"Updating substitutes chat display meetup {meetup_date_time_string}")
            await bot_call_message_function(
                message_function=edit_message_func,
                text=display_meetup.to_string(classified=True),
                chat_id=SUBSTITUTES_ID,
                message_id=message_ids.substitutes_id,
                reply_markup=MEETUP_TELEGRAM_INLINE_KEYBOARD,
            )
        except BadRequest as error:
            error_message = parse_update_request_error(
                meetup_date_time_string=meetup_date_time_string,
                error=error,
            )
            if "Deleting the saved reference" in error_message:
                MeetupToTelegramIdTranslator().save(
                    meetup_id=meetup_id,
                    regulars_id=message_ids.regulars_id,
                    substitutes_id=None,
                )
            await send_message_to_admins(message_function=send_message_func, text=error_message)


def parse_update_request_error(
    meetup_date_time_string: str,
    error: BadRequest,
) -> None:
    if "Message to edit not found" in error.message:
        return (
            f"The display message from the meetup ({meetup_date_time_string}) does not exist."
            " Deleting the saved reference."
        )

    if "Message is not modified" in error.message:
        return f"The display message from the meetup `{meetup_date_time_string}` was not modified."

    return f"Unknown error when updating the meetup ({meetup_date_time_string}) message: {error}"


async def send_regulars_meetup_message(
    meetup_id: uuid.UUID,
    send_message_func: Callable,
    delete_message_func: Callable,
    force: bool = False,
) -> None:
    try:
        existent_message_info: MeetupMessagesIds = MeetupToTelegramIdTranslator().get(
            meetup_id=meetup_id
        )
    except MeetupIdNotFound:
        pass
    else:
        try:
            if force:
                await delete_message_func(
                    chat_id=REGULARS_ID, message_id=existent_message_info.regulars_id
                )
        except (Forbidden, BadRequest) as error:
            logger.error(
                "Error when trying to delete the regulars meetup display message. It does not"
                f" exists or the bot does not have enough permisisons: {error}"
            )

    try:
        message_id = await get_and_display_meetup_in_chat(
            meetup_id=meetup_id,
            chat_id=REGULARS_ID,
            classified=False,
            send_message_func=send_message_func,
        )
    except CouldNotConnectToTheCore:
        return

    MeetupToTelegramIdTranslator().save(meetup_id=meetup_id, regulars_id=message_id)


async def send_substitutes_meetup_message(
    meetup_id: uuid.UUID,
    send_message_func: Callable,
    delete_message_func: Callable,
    force: bool = False,
) -> None:
    try:
        existent_message_info: MeetupMessagesIds = MeetupToTelegramIdTranslator().get(
            meetup_id=meetup_id
        )
    except MeetupIdNotFound:
        await send_message_to_admins(
            message_function=send_message_func,
            text=(
                f"Please, send the regulars display meetup before sending the substitutes message."
            ),
        )
        return

    if force and existent_message_info.substitutes_id is not None:
        try:
            delete_message_func(
                chat_id=SUBSTITUTES_ID, message_id=existent_message_info.substitutes_id
            )
        except (Forbidden, BadRequest) as error:
            logger.error(
                "Error when trying to delete the substitutes meetup display message. It does not"
                f" exists or the bot does not have enough permisisons: {error}"
            )

    try:
        message_id = await get_and_display_meetup_in_chat(
            meetup_id=meetup_id,
            chat_id=SUBSTITUTES_ID,
            classified=True,
            send_message_func=send_message_func,
        )
    except CouldNotConnectToTheCore:
        return

    MeetupToTelegramIdTranslator().save(
        meetup_id=meetup_id,
        regulars_id=existent_message_info.regulars_id,
        substitutes_id=message_id,
    )


async def get_and_display_meetup_in_chat(
    meetup_id: uuid.UUID, chat_id: int, classified: bool, send_message_func: Callable
) -> int:
    try:
        display_meetup: DisplayMeetup = meetup_requests.get_display_meetup(
            id=meetup_id,
        )
    except CouldNotConnectToTheCore as error:
        await send_message_to_admins(
            message_function=send_message_func,
            text=(
                f"There is a problem contacting Pyball core when updating meetup message: {error}"
            ),
        )
        raise

    return (
        await bot_call_message_function(
            message_function=send_message_func,
            text=display_meetup.to_string(classified=classified),
            chat_id=chat_id,
            reply_markup=MEETUP_TELEGRAM_INLINE_KEYBOARD,
        )
    ).message_id
