"""Tests for react_ok helper."""
from unittest.mock import AsyncMock, MagicMock

import pytest
import telegram
from telegram import ReactionTypeEmoji

from pyball.infrastructure.telegram.bot.reactions import react_ok


@pytest.mark.asyncio
async def test_react_ok_calls_set_message_reaction():
    bot = AsyncMock()
    message = MagicMock()
    message.chat_id = 111
    message.message_id = 42

    await react_ok(bot, message)

    bot.set_message_reaction.assert_called_once_with(
        chat_id=111,
        message_id=42,
        reaction=[ReactionTypeEmoji("✅")],
    )


@pytest.mark.asyncio
async def test_react_ok_falls_back_to_reply_on_telegram_error():
    bot = AsyncMock()
    bot.set_message_reaction.side_effect = telegram.error.TelegramError("no reactions")
    message = AsyncMock()
    message.chat_id = 111
    message.message_id = 42

    await react_ok(bot, message)

    message.reply_text.assert_called_once_with("✅")
