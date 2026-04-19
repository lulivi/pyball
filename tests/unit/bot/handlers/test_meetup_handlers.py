"""Tests for meetup bot handlers."""

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from telegram.constants import ParseMode

from pyball.bot.handlers.meetup import (
    create_teams_handler,
    generate_qr_bytes,
    new_meetup_handler,
    show_meetup_handler,
)


def test_generate_qr_bytes_returns_png_buffer():
    buf = generate_qr_bytes("https://example.com/match?date=2026-04-19")
    assert isinstance(buf, BytesIO)
    header = buf.read(4)
    assert header == b"\x89PNG"


@pytest.mark.asyncio
async def test_new_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []

    await new_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Usage: `/new_meetup` `YYYY/MM/DD HH:MM`", parse_mode=ParseMode.MARKDOWN_V2
    )


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Invalid date format. Use: `/new_meetup` `YYYY/MM/DD HH:MM`"
    )


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        r"Usage: `/show_meetup` `YYYY/MM/DD HH:MM`", parse_mode=ParseMode.MARKDOWN_V2
    )


@pytest.mark.asyncio
async def test_show_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["bad", "date"]
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    (text, *_), _ = mock_update.message.reply_text.call_args
    assert "Invalid date format" in text


@pytest.mark.asyncio
async def test_show_meetup_handler_not_found(mock_update, mock_context):
    mock_context.args = ["2026/04/25", "20:00"]

    container = MagicMock()
    container.meetup_repository.find_by_date.return_value = None
    mock_context.bot_data["container"] = container

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Meetup not found.")


@pytest.mark.asyncio
async def test_create_teams_handler_no_teams(mock_update, mock_context):
    mock_context.args = ["2026/04/25", "20:00"]

    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.teams = []
    container.create_teams.return_value.execute.return_value = mock_meetup
    mock_context.bot_data["container"] = container

    await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("No teams created.")
