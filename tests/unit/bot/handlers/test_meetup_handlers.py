"""Tests for meetup bot handlers."""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode

from pyball.bot.handlers.meetup import (
    _date_usage_msg,
    create_teams_handler,
    generate_qr_bytes,
    new_meetup_handler,
    show_meetup_handler,
    start_match_handler,
)
from pyball.domain.meetup.errors import MeetupHasNoTeamsError, MeetupNotFoundError


def test_generate_qr_bytes_returns_png_buffer():
    buf = generate_qr_bytes("https://example.com/match?date=2026-04-19")
    assert isinstance(buf, BytesIO)
    header = buf.read(4)
    assert header == b"\x89PNG"


@pytest.mark.asyncio
async def test_new_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/new_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/new_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/show_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["bad", "date"]
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Ejemplo: `/show_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_not_found(mock_update, mock_context):
    mock_context.args = ["2026-04-25", "20:00"]

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
    mock_context.args = ["2026-04-19", "20:00"]
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
    mock_context.args = ["2026-04-19", "20:00"]
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
    mock_context.args = ["2026-04-25", "20:00"]

    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.teams = []
    container.create_teams.return_value.execute.return_value = mock_meetup
    mock_context.bot_data["container"] = container

    await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("No teams created.")


def test_date_usage_msg_no_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("new_meetup", fmt)
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/new_meetup` `2026-05-01 14:30`"
    )


def test_date_usage_msg_with_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("add_player", fmt, r"`<name1>`, `<name2>`, \.\.\.")
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/add_player` `2026-05-01 14:30` `<name1>`, `<name2>`, \.\.\."
    )


@pytest.mark.asyncio
async def test_start_match_handler_meetup_not_found(mock_update, mock_context):
    """start_match replies in Spanish when no meetup exists for that date."""
    container = MagicMock()
    container.start_match.return_value.execute.side_effect = MeetupNotFoundError(
        "2026-04-19T20:00"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-19", "20:00"]

    await start_match_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "No existe ningún meetup para esa fecha."
    )


@pytest.mark.asyncio
async def test_start_match_handler_no_teams(mock_update, mock_context):
    """start_match replies in Spanish with /create_teams command when meetup has no teams."""
    container = MagicMock()
    container.start_match.return_value.execute.side_effect = MeetupHasNoTeamsError(
        "Meetup has no teams"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-19", "20:00"]
    mock_context.bot_data["settings"].pyball.display_date_format = "%Y-%m-%d %H:%M"

    await start_match_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "no tiene equipos asignados" in text
    assert "/create_teams" in text
    assert "2026-04-19 20:00" in text


@pytest.mark.asyncio
async def test_start_match_handler_unexpected_error(mock_update, mock_context):
    """start_match replies with generic Spanish message and logs on unexpected errors."""
    container = MagicMock()
    container.start_match.return_value.execute.side_effect = RuntimeError("boom")
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-19", "20:00"]

    with patch("pyball.bot.handlers.meetup.logger") as mock_logger:
        await start_match_handler(mock_update, mock_context)

    mock_logger.exception.assert_called_once()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "error inesperado" in text.lower()
