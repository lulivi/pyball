"""Tests for meetup bot handlers."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode, ReactionEmoji

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.infrastructure.telegram.bot.handlers.meetup import (
    _date_usage_msg,
    _do_search,
    search_handler,
    stats_handler,
)


def test_date_usage_msg_no_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("meetup_new", fmt)
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/meetup_new` `2026-05-01 14:30`"
    )


def test_date_usage_msg_with_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("meetup_add_player", fmt, r"`<name1>`, `<name2>`, \.\.\.")
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/meetup_add_player` `2026-05-01 14:30` `<name1>`, `<name2>`, \.\.\."
    )


@pytest.mark.asyncio
async def test_do_search_sends_message_and_tracks_it(mock_context):
    """_do_search sends the substitutes message and stores tracking info."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 4, 25, 20, 0)
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.substitutes.chat_id = -1001234567
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=7))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=None,
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"
        ) as mock_store_cls,
    ):
        await _do_search(meetup, container, bot, settings)

    bot.send_message.assert_called_once_with(
        chat_id=-1001234567,
        text="msg",
        reply_markup=None,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    mock_store_cls.return_value.save_message.assert_called_once()


@pytest.mark.asyncio
async def test_search_handler_success_reacts(mock_update, mock_context):
    """search reacts ✅ and sends no reply_text on success."""
    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.date = datetime(2026, 4, 25, 20, 0)
    container.meetup_repository.find_by_datetime.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -1001234567
    mock_context.args = ["2026-04-25", "20:00"]
    mock_context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=None,
        ),
    ):
        await search_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_search_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """search with no args uses the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.players = []
    meetup.teams = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -100
    mock_context.bot = AsyncMock()
    mock_context.args = []

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=MagicMock(),
        ),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await search_handler(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_search_handler_no_args_no_active_meetup_replies_error(mock_update, mock_context):
    """search with no args replies in Spanish when no active meetup exists."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -100
    mock_context.args = []

    await search_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_stats_handler_success_reacts(mock_update, mock_context):
    """stats reacts ✅ after sending the stats photo."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.regulars.chat_id = 0
    mock_context.args = ["temporada"]
    mock_context.bot.send_photo = AsyncMock()

    cs_path = "pyball.infrastructure.telegram.bot.handlers.meetup.ComputeStats"
    renderer_path = "pyball.infrastructure.telegram.bot.handlers.meetup.StatsHtmlRenderer"
    with patch(cs_path) as mock_cs, patch(renderer_path) as mock_renderer:
        mock_cs.return_value.execute.return_value = MagicMock()
        mock_renderer.return_value.render = AsyncMock(return_value=b"fakepng")

        await stats_handler(mock_update, mock_context)

    mock_context.bot.send_photo.assert_called_once()
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
