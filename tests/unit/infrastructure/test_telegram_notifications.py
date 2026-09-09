"""Tests for TelegramMatchNotifier."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import telegram

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram import notifications
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore
from pyball.infrastructure.telegram.notifications import TelegramMatchNotifier


def _make_notifier(tmp_path):
    """Build a TelegramMatchNotifier with mocked bot, settings, and container."""
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 555
    settings = MagicMock()
    settings.paths.data_dir = tmp_path
    settings.pyball.team_colors = ("blanco", "negro")
    settings.pyball.team_emojis = ("⚪", "⚫")
    settings.pyball.display_date_format = "%Y-%m-%d %H:%M"
    settings.telegram.regulars.chat_id = -100
    settings.telegram.regulars.meetups_thread_id = ""
    settings.telegram.activity.chat_id = -300
    settings.telegram.activity.thread_id = ""
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    return TelegramMatchNotifier(bot, settings, container), bot


@pytest.mark.asyncio
async def test_on_meetup_created_sends_only_regulars_message(tmp_path):
    """on_meetup_created posts to the regulars chat and tracks the message, never subs."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")

    await notifier.on_meetup_created(meetup)

    bot.send_message.assert_called_once()
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["reply_markup"] is not None

    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    assert store.get_message(meetup.date, "regular") is not None
    assert store.get_message(meetup.date, "substitute") is None


@pytest.mark.asyncio
async def test_on_meetup_created_swallows_telegram_error(tmp_path):
    """A Telegram send failure is logged and swallowed, not raised."""
    notifier, bot = _make_notifier(tmp_path)
    bot.send_message.side_effect = telegram.error.TelegramError("boom")
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")

    await notifier.on_meetup_created(meetup)  # must not raise

    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    assert store.get_message(meetup.date, "regular") is None


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


@pytest.mark.asyncio
async def test_on_meetup_updated_hides_keyboard_when_teams_exist(tmp_path):
    """on_meetup_updated omits the join/leave keyboard once teams are assigned."""
    from pyball.domain.meetup.models import Team
    from pyball.domain.player.models import PlayerId

    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 30, 20, 0), "regular", MessageTracking(chat_id=-100, message_id=42)
    )

    await notifier.on_meetup_updated(meetup)

    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_on_meetup_date_changed_rekeys_and_refreshes_tracked_message(tmp_path):
    """on_meetup_date_changed re-keys the store entry and edits the message in place."""
    notifier, bot = _make_notifier(tmp_path)
    old_date = datetime(2026, 4, 30, 20, 0)
    new_date = datetime(2026, 5, 7, 20, 0)
    meetup = Meetup.create(new_date, "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(old_date, "regular", MessageTracking(chat_id=-100, message_id=42))

    await notifier.on_meetup_date_changed(old_date, meetup)

    assert store.get_message(old_date, "regular") is None
    assert store.get_message(new_date, "regular") is not None
    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["chat_id"] == -100
    assert kwargs["message_id"] == 42


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


@pytest.mark.asyncio
async def test_on_player_joined_sends_activity_message_titular(tmp_path):
    """on_player_joined posts an Alta message with titular status to the activity chat."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_joined(meetup, player, False)

    bot.send_message.assert_called_once()
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == -300
    assert "Alta" in kwargs["text"]
    assert "Carlos" in kwargs["text"]
    assert "titular" in kwargs["text"]


@pytest.mark.asyncio
async def test_on_player_joined_sends_activity_message_suplente(tmp_path):
    """on_player_joined labels the player as suplente when is_substitute is True."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Ana", "regular")

    await notifier.on_player_joined(meetup, player, True)

    kwargs = bot.send_message.call_args.kwargs
    assert "suplente" in kwargs["text"]


@pytest.mark.asyncio
async def test_on_player_joined_escapes_backtick_in_player_name(tmp_path):
    """A backtick in the player's name is escaped so it can't break the MarkdownV2 code span."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos`DROP", "regular")

    await notifier.on_player_joined(meetup, player, False)

    kwargs = bot.send_message.call_args.kwargs
    assert "Carlos\\`DROP" in kwargs["text"]


@pytest.mark.asyncio
async def test_on_player_left_sends_activity_message(tmp_path):
    """on_player_left posts a Baja message to the activity chat."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_left(meetup, player, False)

    bot.send_message.assert_called_once()
    kwargs = bot.send_message.call_args.kwargs
    assert "Baja" in kwargs["text"]
    assert "Carlos" in kwargs["text"]


@pytest.mark.asyncio
async def test_on_player_joined_uses_configured_thread_id(tmp_path):
    """message_thread_id is set (as an int) when activity.thread_id is configured."""
    notifier, bot = _make_notifier(tmp_path)
    notifier._settings.telegram.activity.thread_id = "9"  # pylint: disable=protected-access
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_joined(meetup, player, False)

    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["message_thread_id"] == 9


@pytest.mark.asyncio
async def test_on_player_joined_does_nothing_when_activity_chat_unset(tmp_path):
    """No message is sent when telegram.activity.chat_id is not configured."""
    notifier, bot = _make_notifier(tmp_path)
    notifier._settings.telegram.activity.chat_id = 0  # pylint: disable=protected-access
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_joined(meetup, player, False)

    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_on_player_left_swallows_telegram_error(tmp_path):
    """A Telegram send failure is logged and swallowed, not raised."""
    notifier, bot = _make_notifier(tmp_path)
    bot.send_message.side_effect = telegram.error.TelegramError("boom")
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_left(meetup, player, False)  # must not raise
