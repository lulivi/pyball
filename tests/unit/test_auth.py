from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import Message, Update, User
from telegram.ext import ContextTypes

from pyball.bot.auth import authorized


@pytest.fixture
def mock_update():
    user = MagicMock(spec=User)
    user.id = 123
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.message = message
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.mark.asyncio
async def test_authorized_allows_admin_user(mock_update, mock_context):
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    mock_context.bot_data = {"settings": settings}

    @authorized
    async def handler(update, context):
        return "success"

    result = await handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_authorized_blocks_non_admin_user(mock_update, mock_context):
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = False
    mock_context.bot_data = {"settings": settings}

    @authorized
    async def handler(update, context):
        return "success"

    result = await handler(mock_update, mock_context)
    assert result is None
    mock_update.message.reply_text.assert_called_once_with(
        "Unauthorized. You don't have permission to use this bot."
    )
