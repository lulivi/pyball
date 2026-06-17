"""Tests for TelegramMatchNotifier."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.telegram import notifications
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore
from pyball.infrastructure.telegram.notifications import TelegramMatchNotifier


def _make_notifier(tmp_path):
    """Build a TelegramMatchNotifier with mocked bot, settings, and container."""
    bot = AsyncMock()
    settings = MagicMock()
    settings.paths.data_dir = tmp_path
    settings.pyball.team_colors = ("blanco", "negro")
    settings.pyball.team_emojis = ("⚪", "⚫")
    settings.pyball.display_date_format = "%Y-%m-%d %H:%M"
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    return TelegramMatchNotifier(bot, settings, container), bot


@pytest.mark.asyncio
async def test_on_meetup_updated_edits_tracked_regular_message(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )

    await notifier.on_meetup_updated(meetup)

    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["chat_id"] == -100
    assert kwargs["message_id"] == 42
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_on_meetup_updated_does_nothing_when_no_tracked_messages(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")

    await notifier.on_meetup_updated(meetup)

    bot.edit_message_text.assert_not_called()


def _discard_task(coro):
    """Close the coroutine so it is never scheduled and emits no warnings."""
    coro.close()


@pytest.mark.asyncio
async def test_on_match_closed_edits_without_keyboard(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )

    with patch(
        "pyball.infrastructure.telegram.notifications.asyncio.create_task",
        side_effect=_discard_task,
    ):
        await notifier.on_match_closed(meetup)

    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_on_match_closed_deletes_tracking_entries(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "substitute", MessageTracking(chat_id=-200, message_id=99)
    )

    with patch(
        "pyball.infrastructure.telegram.notifications.asyncio.create_task",
        side_effect=_discard_task,
    ):
        await notifier.on_match_closed(meetup)

    assert store.get_message(datetime(2026, 4, 30, 20, 0), "regular") is None
    assert store.get_message(datetime(2026, 4, 30, 20, 0), "substitute") is None


@pytest.mark.asyncio
async def test_on_match_edited_sends_new_message_and_reposts_stats(monkeypatch):
    """on_match_edited sends a fresh corrected-result message and refreshes stats."""
    stats_calls = []

    async def _fake_stats(bot, container, settings):
        stats_calls.append((bot, container, settings))

    monkeypatch.setattr(notifications, "_post_match_stats", _fake_stats)

    bot = AsyncMock()
    settings = MagicMock()
    settings.pyball.team_colors = ("blanco", "negro")
    settings.pyball.team_emojis = ("⚪", "⚫")
    settings.telegram.regulars.chat_id = -100123
    settings.telegram.regulars.meetups_thread_id = ""
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    container.format_match_summary.return_value.execute.return_value = "resumen"

    notifier = notifications.TelegramMatchNotifier(bot, settings, container)
    await notifier.on_match_edited(MagicMock())
    await asyncio.sleep(0)  # let the fire-and-forget stats task run

    bot.send_message.assert_awaited_once()
    kwargs = bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == -100123
    assert "Resultado corregido" in kwargs["text"]
    assert "resumen" in kwargs["text"]
    assert len(stats_calls) == 1


@pytest.mark.asyncio
async def test_on_meetup_cancelled_edits_regular_message_with_cancelado_prefix(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )

    await notifier.on_meetup_cancelled(meetup)

    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["chat_id"] == -100
    assert kwargs["message_id"] == 42
    assert kwargs["reply_markup"] is None
    assert "CANCELADO" in kwargs["text"]


@pytest.mark.asyncio
async def test_on_meetup_cancelled_edits_both_messages_with_cancelado_prefix(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "substitute", MessageTracking(chat_id=-200, message_id=99)
    )

    await notifier.on_meetup_cancelled(meetup)

    assert bot.edit_message_text.call_count == 2
    for call in bot.edit_message_text.call_args_list:
        assert call.kwargs["reply_markup"] is None
        assert "CANCELADO" in call.kwargs["text"]
    chat_ids = {c.kwargs["chat_id"] for c in bot.edit_message_text.call_args_list}
    assert chat_ids == {-100, -200}


@pytest.mark.asyncio
async def test_on_meetup_cancelled_deletes_tracking_entries(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "substitute", MessageTracking(chat_id=-200, message_id=99)
    )

    await notifier.on_meetup_cancelled(meetup)

    assert store.get_message(datetime(2026, 4, 30, 20, 0), "regular") is None
    assert store.get_message(datetime(2026, 4, 30, 20, 0), "substitute") is None


@pytest.mark.asyncio
async def test_on_meetup_cancelled_does_nothing_when_no_tracked_messages(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")

    await notifier.on_meetup_cancelled(meetup)

    bot.edit_message_text.assert_not_called()
