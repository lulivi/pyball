"""Tests for TelegramMatchNotifier."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import telegram

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player, PlayerId
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
    settings.telegram.regulars.meetups.chat_id = -100
    settings.telegram.regulars.meetups.message_thread_id = None
    settings.telegram.regulars.stats.chat_id = -200
    settings.telegram.regulars.stats.message_thread_id = None
    settings.telegram.management.activity.chat_id = -300
    settings.telegram.management.activity.message_thread_id = None
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    return TelegramMatchNotifier(bot, settings, container), bot


@pytest.mark.asyncio
async def test_on_meetup_created_sends_regulars_and_activity_messages(tmp_path):
    """on_meetup_created posts the regulars callup and a 'creada' line to the activity feed."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")

    await notifier.on_meetup_created(meetup)

    assert bot.send_message.call_count == 2
    assert bot.send_message.call_args_list[0].kwargs["reply_markup"] is not None
    activity_call = bot.send_message.call_args_list[1]
    assert activity_call.kwargs["chat_id"] == -300
    assert "Convocatoria creada" in activity_call.kwargs["text"]

    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    assert store.get_message(meetup.date, "regular") is not None
    assert store.get_message(meetup.date, "substitute") is None


@pytest.mark.asyncio
async def test_on_meetup_created_skips_activity_when_unconfigured(tmp_path):
    """With no activity chat, on_meetup_created sends only the regulars callup."""
    from pyball.infrastructure.telegram.settings import ChatConfig

    notifier, bot = _make_notifier(tmp_path)
    # pylint: disable-next=protected-access
    notifier._settings.telegram.management.activity = ChatConfig()
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")

    await notifier.on_meetup_created(meetup)

    assert bot.send_message.call_count == 1


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
async def test_on_meetup_updated_keeps_subs_keyboard_while_search_open(tmp_path):
    """The substitutes message keeps its keyboard while the search is open."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo", capacity=15)
    for _ in range(13):
        meetup.add_player(PlayerId.generate())
    meetup.open_substitute_search()
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(meetup.date, "substitute", MessageTracking(chat_id=-200, message_id=99))

    await notifier.on_meetup_updated(meetup)

    subs_edit = next(
        c for c in bot.edit_message_text.call_args_list if c.kwargs["message_id"] == 99
    )
    assert subs_edit.kwargs["reply_markup"] is not None
    assert "13/15" in subs_edit.kwargs["text"]


@pytest.mark.asyncio
async def test_on_meetup_updated_strips_subs_keyboard_once_search_closed(tmp_path):
    """The substitutes message loses its keyboard once the search is closed."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo", capacity=15)
    for _ in range(12):
        meetup.add_player(PlayerId.generate())
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(meetup.date, "substitute", MessageTracking(chat_id=-200, message_id=99))

    await notifier.on_meetup_updated(meetup)

    subs_edit = next(
        c for c in bot.edit_message_text.call_args_list if c.kwargs["message_id"] == 99
    )
    assert subs_edit.kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_on_substitute_search_opened_posts_and_tracks_subs_message(tmp_path):
    """Opening a search posts the substitutes callup with its keyboard and tracks it."""
    notifier, bot = _make_notifier(tmp_path)
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=55))
    notifier._settings.telegram.substitutes.meetups.chat_id = -400  # pylint: disable=W0212
    notifier._settings.telegram.substitutes.meetups.message_thread_id = (
        None  # pylint: disable=W0212
    )
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")
    meetup.open_substitute_search()

    await notifier.on_substitute_search_opened(meetup)

    assert bot.send_message.call_args.kwargs["reply_markup"] is not None
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    assert store.get_message(meetup.date, "substitute").message_id == 55


@pytest.mark.asyncio
async def test_on_substitute_search_opened_without_subs_chat_sends_nothing(tmp_path):
    """With no substitutes chat configured, opening a search posts nothing."""
    notifier, bot = _make_notifier(tmp_path)
    notifier._settings.telegram.substitutes.meetups = None  # pylint: disable=protected-access
    meetup = Meetup.create(datetime(2026, 4, 30, 20, 0), "Campo")

    await notifier.on_substitute_search_opened(meetup)

    bot.send_message.assert_not_called()


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


@pytest.mark.asyncio
async def test_on_meetup_date_changed_hides_keyboard_when_teams_exist(tmp_path):
    """on_meetup_date_changed omits the join/leave keyboard once teams are assigned."""
    from pyball.domain.meetup.models import Team
    from pyball.domain.player.models import PlayerId

    notifier, bot = _make_notifier(tmp_path)
    old_date = datetime(2026, 4, 30, 20, 0)
    new_date = datetime(2026, 5, 7, 20, 0)
    meetup = Meetup.create(new_date, "Campo")
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(old_date, "regular", MessageTracking(chat_id=-100, message_id=42))

    await notifier.on_meetup_date_changed(old_date, meetup)

    bot.edit_message_text.assert_called_once()
    kwargs = bot.edit_message_text.call_args.kwargs
    assert kwargs["reply_markup"] is None


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
async def test_on_match_closed_posts_closed_line_to_activity(tmp_path):
    """on_match_closed posts a 'cerrada' line to the activity feed."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        meetup.date,
        "regular",
        MessageTracking(chat_id=-100, thread_id=None, message_id=1),
    )
    with patch.object(notifications, "_post_match_stats", new=AsyncMock()):
        await notifier.on_match_closed(meetup)

    texts = [c.kwargs.get("text", "") for c in bot.send_message.call_args_list]
    assert any("Convocatoria cerrada" in t for t in texts)
    assert any(c.kwargs.get("chat_id") == -300 for c in bot.send_message.call_args_list)


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
    settings.telegram.regulars.meetups.chat_id = -100123
    settings.telegram.regulars.meetups.message_thread_id = None
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
async def test_on_meetup_cancelled_posts_cancelled_line_to_activity(tmp_path):
    """on_meetup_cancelled posts a 'cancelada' line to the activity feed."""
    notifier, bot = _make_notifier(tmp_path)
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    store = TelegramMessageStore(tmp_path / "bot" / "messages.json")
    store.save_message(
        meetup.date,
        "regular",
        MessageTracking(chat_id=-100, thread_id=None, message_id=1),
    )
    await notifier.on_meetup_cancelled(meetup)

    texts = [c.kwargs.get("text", "") for c in bot.send_message.call_args_list]
    assert any("Convocatoria cancelada" in t for t in texts)


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
    """message_thread_id is passed through when management.activity has a topic."""
    notifier, bot = _make_notifier(tmp_path)
    # pylint: disable-next=protected-access
    notifier._settings.telegram.management.activity.message_thread_id = 9
    meetup = Meetup.create(datetime(2026, 8, 3, 20, 0), "Campo")
    player = Player.create("Carlos", "regular")

    await notifier.on_player_joined(meetup, player, False)

    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["message_thread_id"] == 9


@pytest.mark.asyncio
async def test_on_player_joined_does_nothing_when_activity_chat_unset(tmp_path):
    """No message is sent when the activity chat is not configured."""
    from pyball.infrastructure.telegram.settings import ChatConfig

    notifier, bot = _make_notifier(tmp_path)
    # pylint: disable-next=protected-access
    notifier._settings.telegram.management.activity = ChatConfig()
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


@pytest.mark.asyncio
async def test_post_match_stats_noop_when_stats_chat_unset(tmp_path):
    """_post_match_stats returns immediately when regulars.stats is not configured."""
    from pyball.infrastructure.telegram.settings import ChatConfig

    _, bot = _make_notifier(tmp_path)
    settings = MagicMock()
    settings.telegram.regulars.stats = ChatConfig()
    container = MagicMock()

    await notifications._post_match_stats(bot, container, settings)

    bot.send_photo.assert_not_called()


@pytest.mark.asyncio
async def test_post_match_stats_posts_to_stats_chat_not_meetups_chat(tmp_path):
    """_post_match_stats sends the image to regulars.stats, with its own thread id."""
    from pyball.infrastructure.telegram.settings import ChatConfig

    _, bot = _make_notifier(tmp_path)
    settings = MagicMock()
    settings.telegram.regulars.meetups = ChatConfig(chat_id=-100)
    settings.telegram.regulars.stats = ChatConfig(chat_id=-200, message_thread_id=99)
    container = MagicMock()

    cs_path = "pyball.infrastructure.telegram.notifications.ComputeStats"
    renderer_path = "pyball.infrastructure.telegram.notifications.StatsHtmlRenderer"
    with patch(cs_path) as mock_cs, patch(renderer_path) as mock_renderer:
        mock_cs.return_value.execute.return_value = MagicMock()
        mock_renderer.return_value.render = AsyncMock(return_value=b"fakepng")

        await notifications._post_match_stats(bot, container, settings)

    bot.send_photo.assert_called_once()
    kwargs = bot.send_photo.call_args.kwargs
    assert kwargs["chat_id"] == -200
    assert kwargs["message_thread_id"] == 99
