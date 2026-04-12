"""Tests for meetup bot handlers."""

import pytest

from pyball.bot.handlers.meetup import new_meetup_handler


@pytest.mark.asyncio
async def test_new_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []

    await new_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Usage: /new_meetup `YYYY/MM/DD HH:MM`")


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Invalid date format. Use: /new_meetup `YYYY/MM/DD HH:MM`"
    )
