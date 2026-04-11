from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import Message, Update
from telegram.ext import ContextTypes

from pyball.bot.handlers.meetup import new_meetup_handler


@pytest.mark.asyncio
async def test_new_meetup_handler_no_args():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    await new_meetup_handler(update, context)

    update.message.reply_text.assert_called_with("Usage: /new_meetup YYYY-MM-DD HH:MM")


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["invalid-date"]

    await new_meetup_handler(update, context)

    update.message.reply_text.assert_called_with(
        "Invalid date format. Use: /new_meetup YYYY-MM-DD HH:MM"
    )
