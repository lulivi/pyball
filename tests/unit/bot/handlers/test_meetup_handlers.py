"""Tests for meetup bot handlers."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode

from pyball.bot.handlers.meetup import (
    create_teams_handler,
    generate_qr_bytes,
    new_meetup_handler,
    show_meetup_handler,
    start_match_handler,
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
        text="Usage: `/new_meetup` `YYYY/MM/DD HH:MM`", parse_mode=ParseMode.MARKDOWN_V2
    )


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    assert call.args[0] == r"Invalid date format\. Use: `/new_meetup` `YYYY/MM/DD HH:MM`"
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        text=r"Usage: `/show_meetup` `YYYY/MM/DD HH:MM`", parse_mode=ParseMode.MARKDOWN_V2
    )


@pytest.mark.asyncio
async def test_show_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["bad", "date"]
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
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
async def test_start_match_handler_sends_qr_photo(mock_update, mock_context):
    url = "https://pyball.example.com/?date=2026-04-19T20%3A00&teamA=Ana&teamB=Bob"
    admin_id = 99999

    container = MagicMock()
    container.start_match.return_value.execute.return_value = url
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026/04/19", "20:00"]
    mock_context.bot_data["settings"].telegram.admins_ids = [admin_id]
    mock_context.bot = AsyncMock()
    mock_context.bot.send_photo = AsyncMock()

    fake_buf = BytesIO(b"fakepng")

    with patch("pyball.bot.handlers.meetup.generate_qr_bytes", return_value=fake_buf) as mock_qr:
        await start_match_handler(mock_update, mock_context)

    mock_qr.assert_called_once_with(url)
    mock_context.bot.send_photo.assert_called_once_with(
        chat_id=admin_id,
        photo=fake_buf,
        caption=f"🔗 Enlace del partido:\n{url}",
    )


@pytest.mark.asyncio
async def test_start_match_handler_sends_qr_to_each_admin(mock_update, mock_context):
    url = "https://pyball.example.com/?date=2026-04-19T20%3A00&teamA=Ana&teamB=Bob"
    admin_ids = [11111, 22222]

    container = MagicMock()
    container.start_match.return_value.execute.return_value = url
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026/04/19", "20:00"]
    mock_context.bot_data["settings"].telegram.admins_ids = admin_ids
    mock_context.bot = AsyncMock()
    mock_context.bot.send_photo = AsyncMock()

    fake_buf = BytesIO(b"fakepng")

    with patch("pyball.bot.handlers.meetup.generate_qr_bytes", return_value=fake_buf):
        await start_match_handler(mock_update, mock_context)

    assert mock_context.bot.send_photo.call_count == 2
    calls = mock_context.bot.send_photo.call_args_list
    assert calls[0].kwargs["chat_id"] == 11111
    assert calls[1].kwargs["chat_id"] == 22222
    assert calls[0].kwargs["photo"] is fake_buf
    assert calls[1].kwargs["photo"] is fake_buf


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
