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

"""Bot commands and buttons."""

from typing import Optional

from telegram import Update
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from pyball.bot.callup import CALL_UP_KEYBOARD, CallUp
from pyball.bot.errors import (
    CommandArgumentError,
    ExpectedMessageIdError,
    NoCallUpError,
    NotAdminError,
    PlayerAlreadyCalledUpError,
    PlayerNotCalledUpError,
)
from pyball.bot.utils import (
    bot_call_message_function,
    ensure_admin,
    get_command_argument,
    search_substitutes,
    validate_call_up_message_id,
)


async def command_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides information about the bot usage.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    await update.message.reply_text(
        "¡Hola! Este bot puede ayudarte a organizar tu convocatoria.\n- Utiliza el comando /new"
        " para iniciar una nueva convocatoria o reiniciar la anterior.\n- Utiliza el comando /add"
        " <nombre> para añadir a una persona manualmente o /del <nombre> para eliminarla"
        " respondiendo al mensaje de la convocatoria.\n- Utiliza el comando /search para buscar"
        " suplentes para el partido."
    )


async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates a new call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    try:
        title = get_command_argument(
            update.message.text, "new", "título de la convocatoria", "10/10/10 20h", True
        )
        ensure_admin(update.message.from_user.id)
    except (CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    chat_id = update.message.chat_id
    chat_message = (
        await bot_call_message_function(
            update.message.reply_text, f"Lista de jugadores para la convocatoria *{title}*"
        )
    ).message_id

    context.chat_data["call-up"] = CallUp(title, chat_id, chat_message)


async def button_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manages the player actions of joning and leaving the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    query = update.callback_query
    call_up: CallUp = context.chat_data.get("call-up")

    try:
        validate_call_up_message_id(call_up, query.message)
    except (NoCallUpError, ExpectedMessageIdError):
        await query.answer(
            text="Por favor, utiliza sólamente la última convocatoria. Ésta está ya cerrada.",
        )
        return

    player = update.effective_user.full_name
    answer: Optional[str] = None

    try:
        call_up.act(query.data, player)
    except (PlayerAlreadyCalledUpError, PlayerNotCalledUpError) as error:
        answer = str(error)
        return
    finally:
        await query.answer(answer)

    await bot_call_message_function(query.edit_message_text, str(call_up))
    await search_substitutes(
        call_up=call_up,
        reply_function=query.message.reply_text,
        bot=context.bot,
    )


async def command_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a new player to the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        player = get_command_argument(
            update_message_text=update.message.text,
            command_name="add",
            argument_name="player name",
            argument_example="Antonio Manuel",
            required=True,
        )
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    try:
        call_up.add_player(player)
    except PlayerAlreadyCalledUpError:
        return

    await bot_call_message_function(update.message.reply_to_message.edit_text, str(call_up))
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
    )


async def command_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a player from the call-up.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        player = get_command_argument(
            update_message_text=update.message.text,
            command_name="del",
            argument_name="player name",
            argument_example="Antonio Manuel",
            required=True,
        )
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, CommandArgumentError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    try:
        call_up.del_player(player)
    except PlayerNotCalledUpError:
        return

    await bot_call_message_function(update.message.reply_to_message.edit_text, str(call_up))
    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.Bot,
    )


async def command_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for substitute players.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    await search_substitutes(
        call_up=call_up,
        reply_function=update.message.reply_text,
        bot=context.bot,
        force=True,
    )


async def command_stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the player search.

    :param update: The event that caused the bot petition.
    :param context: The information related to the update.

    """
    call_up: CallUp = context.chat_data.get("call-up")
    try:
        validate_call_up_message_id(call_up, update.message.reply_to_message)
        ensure_admin(update.message.from_user.id)
    except (NoCallUpError, ExpectedMessageIdError, NotAdminError) as error:
        await update.message.reply_text(str(error))
        return

    if not call_up.is_searching():
        return

    try:
        await context.bot.delete_message(call_up.subs_chat.chat_id, call_up.subs_chat.msg_id)
    except Forbidden as error:
        await bot_call_message_function(
            update.message.reply_text,
            "El bot no tiene los permisos suficientes para eliminar el mensaje del chat de"
            f" suplentes:\n\t{str(error)}",
        )
        return

    call_up.set_subs_message_id(None)
    await bot_call_message_function(
        update.message.reply_text, "Se ha detenido la búsqueda de suplentes."
    )
