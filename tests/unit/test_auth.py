from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import Message, Update, User
from telegram.ext import ContextTypes

from pyball.bot.auth import authorized


@pytest.mark.asyncio
async def test_authorized_allows_admin_user():
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True

    user = MagicMock(spec=User)
    user.id = 123
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    upd = MagicMock(spec=Update)
    upd.effective_user = user
    upd.message = message
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.bot_data = {"settings": settings}

    @authorized
    async def handler(up, co):
        return "success"

    result = await handler(upd, ctx)
    assert result == "success"


@pytest.mark.asyncio
async def test_authorized_blocks_non_admin_user():
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = False

    user = MagicMock(spec=User)
    user.id = 123
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    upd = MagicMock(spec=Update)
    upd.effective_user = user
    upd.message = message
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    ctx.bot_data = {"settings": settings}

    @authorized
    async def handler(up, co):
        return "success"

    result = await handler(upd, ctx)
    assert result is None
    upd.message.reply_text.assert_called_once_with(
        "Unauthorized. You don't have permission to run this command."
    )
