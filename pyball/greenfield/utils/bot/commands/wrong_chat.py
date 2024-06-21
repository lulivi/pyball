from telegram import Update
from telegram.ext import ContextTypes

from pyball import __version__
from pyball.greenfield.utils.bot.utils import bot_call_message_function
from pyball.logger import log_func


@log_func
async def wrong_chat(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Message from wrong chat.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    if update.message is None:
        return

    await bot_call_message_function(
        update.message.reply_text,
        (
            "¡Hola! Este bot está ejecutando el código alojado en"
            " [gitlab](https://gitlab.com/lulivi/pyball)\.\nÉchale un vistazo a la [introducción"
            " de la API"
            "](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Introduction-to-the-API)"
            " para crear tu bot. Lee el README.md en la raiz del repositorio"
        ),
    )
