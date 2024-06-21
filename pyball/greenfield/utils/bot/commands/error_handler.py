import html
import json
import logging
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from pyball import __version__
from pyball.logger import log_func
from pyball.settings import ADMINS_IDS

logger = logging.getLogger(__name__)


@log_func
async def command_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the admins.

    :param update: The object that caused the exception.
    :param context: Error information.

    """
    if context.error is None:
        logger.error("Exception while handling an update. Counld not get any error information")
        return

    logger.error("Exception while handling an update:", exc_info=context.error)

    traceback_str = html.escape(
        "".join(
            traceback.format_exception(
                None,
                context.error,
                context.error.__traceback__,
            )
        )
    )

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = html.escape(
        json.dumps(
            update.to_dict() if isinstance(update, Update) else str(update),
            indent=2,
            ensure_ascii=False,
        )
    )
    update_message = f"<pre>update = {update_str}</pre>"
    error_message = f"<pre>{html.escape(traceback_str)}</pre>"

    for admin_id in ADMINS_IDS:
        await context.bot.send_message(
            chat_id=admin_id, text="An exception was raised while handling an update"
        )
        await context.bot.send_message(
            chat_id=admin_id, text=update_message, parse_mode=ParseMode.HTML
        )
        await context.bot.send_message(
            chat_id=admin_id, text=error_message, parse_mode=ParseMode.HTML
        )
