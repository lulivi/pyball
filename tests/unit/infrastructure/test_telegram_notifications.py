"""Tests for TelegramMatchNotifier."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore
from pyball.infrastructure.telegram.notifications import TelegramMatchNotifier


def _make_notifier(tmp_path):
    """Build a TelegramMatchNotifier with mocked bot, settings, and container."""
    bot = AsyncMock()
    settings = MagicMock()
    settings.paths.bot_messages_file = tmp_path / "messages.json"
    settings.pyball.team_display_names = ("A", "B")
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    return TelegramMatchNotifier(bot, settings, container), bot


@pytest.mark.asyncio
async def test_on_meetup_updated_edits_tracked_regular_message(tmp_path):
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "messages.json")
    store.save_message("2026-04-30T20:00", "regular", MessageTracking(chat_id=-100, message_id=42))

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
    store = TelegramMessageStore(tmp_path / "messages.json")
    store.save_message("2026-04-30T20:00", "regular", MessageTracking(chat_id=-100, message_id=42))

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
    store = TelegramMessageStore(tmp_path / "messages.json")
    store.save_message("2026-04-30T20:00", "regular", MessageTracking(chat_id=-100, message_id=42))
    store.save_message(
        "2026-04-30T20:00", "substitute", MessageTracking(chat_id=-200, message_id=99)
    )

    with patch(
        "pyball.infrastructure.telegram.notifications.asyncio.create_task",
        side_effect=_discard_task,
    ):
        await notifier.on_match_closed(meetup)

    assert store.get_message("2026-04-30T20:00", "regular") is None
    assert store.get_message("2026-04-30T20:00", "substitute") is None
