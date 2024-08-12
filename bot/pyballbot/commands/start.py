# https://core.telegram.org/bots/features#deep-linking

# "https://t.me/{bot_username}?start=some_command"


from typing import Callable, Dict

from telegram import Update
from telegram.ext import ContextTypes

from pyballbot import __version__
from pyballbot.commands.help import command_help
from pyballbot.logger import log_func
from pyballbot.utils import bot_call_message_function, is_admin_chat


@log_func
async def command_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    redirected_command = update.message.text.replace("/start", "").strip()

    available_commands: Dict[str, Callable] = {}

    if redirected_command in available_commands:
        return await available_commands[redirected_command]()

    await command_help(update, _)
