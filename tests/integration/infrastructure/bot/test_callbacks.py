"""Integration tests for the inline callback handler."""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update, User

from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.telegram.bot.callbacks import callback_handler
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore

# pylint: disable=redefined-outer-name


@pytest.fixture
def callback_update():
    """Build Update mock with callback_query for inline button tests."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.message = AsyncMock(spec=Message)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    user = MagicMock(spec=User)
    user.id = 12345
    query.from_user = user
    update.callback_query = query
    update.effective_user = user
    return update


@pytest.fixture
def linked_player(bot_context):
    """Create a player in the repo and link telegram_id 12345 to it."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")
    store.set_player_id(12345, str(player.id.value))
    return player


@pytest.fixture
def saved_meetup(bot_context):
    """Create and persist a meetup on 2026-04-25 20:00."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)
    return meetup


@pytest.mark.asyncio
async def test_join_adds_player_to_meetup(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Join callback adds the linked player to the meetup and edits the message."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert linked_player.id in meetup.players
    callback_update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_leave_removes_player_from_meetup(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Leave callback removes the linked player from the meetup."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert linked_player.id not in meetup.players
    callback_update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_join_duplicate_answers_already_joined(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Join callback answers already-joined message when player is already in meetup."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    call_kwargs = callback_update.callback_query.answer.call_args
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "ya estás unido" in text.lower()


@pytest.mark.asyncio
async def test_leave_not_in_meetup_answers(
    callback_update,
    bot_context,
    linked_player,  # pylint: disable=unused-argument
    saved_meetup,  # pylint: disable=unused-argument
):
    """Leave callback answers 'No estás en este meetup' when player is not in meetup."""
    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    call_kwargs = callback_update.callback_query.answer.call_args
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "No estás en este meetup" in text


@pytest.mark.asyncio
async def test_unlinked_player_answers_registration_message(
    callback_update, bot_context, saved_meetup  # pylint: disable=unused-argument
):
    """Callback answers with a registration prompt when telegram_id has no mapping."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    call_kwargs = callback_update.callback_query.answer.call_args
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "vinculado" in text.lower() or "ningún jugador" in text.lower()


@pytest.mark.asyncio
async def test_join_clears_teams_when_teams_exist(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Join callback clears existing teams from the meetup."""
    container = bot_context.bot_data["container"]
    extra_id = PlayerId.generate()
    saved_meetup.add_player(extra_id)
    saved_meetup.set_teams([Team.create("A", [extra_id]), Team.create("B", [])])
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup.teams is None


@pytest.mark.asyncio
async def test_leave_clears_teams_when_teams_exist(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Leave callback clears existing teams from the meetup."""
    container = bot_context.bot_data["container"]
    extra_id = PlayerId.generate()
    saved_meetup.add_player(linked_player.id)
    saved_meetup.add_player(extra_id)
    saved_meetup.set_teams([Team.create("A", [linked_player.id]), Team.create("B", [extra_id])])
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup.teams is None


@pytest.mark.asyncio
async def test_invalid_callback_data_answers_error(callback_update, bot_context):
    """Callback answers with error when callback_data has no colon separator."""
    callback_update.callback_query.data = "invalid_data_no_colon"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    call_kwargs = callback_update.callback_query.answer.call_args
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "no válid" in text.lower() or "inválid" in text.lower()


@pytest.mark.asyncio
async def test_join_logs_info_event(
    callback_update,
    bot_context,
    linked_player,  # pylint: disable=unused-argument
    saved_meetup,  # pylint: disable=unused-argument
    caplog,
):
    """Join callback logs an INFO event with player name."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    with caplog.at_level(logging.INFO, logger="pyball.infrastructure.telegram.bot.callbacks"):
        await callback_handler(callback_update, bot_context)

    assert any(
        "joined" in r.message.lower() or "luis" in r.message.lower() for r in caplog.records
    )


@pytest.mark.asyncio
async def test_leave_logs_info_event(
    callback_update,
    bot_context,
    linked_player,
    saved_meetup,
    caplog,
):
    """Leave callback logs an INFO event with player name."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    with caplog.at_level(logging.INFO, logger="pyball.infrastructure.telegram.bot.callbacks"):
        await callback_handler(callback_update, bot_context)

    assert any("left" in r.message.lower() or "luis" in r.message.lower() for r in caplog.records)


@pytest.fixture
def meetup_with_players(bot_context):
    """Create and persist a meetup with 4 players (enough for balanced teams)."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for name in ["Alice", "Bob", "Carlos", "Diana"]:
        player = Player.create(name, "regular")
        container.player_repository.save(player)
        meetup.add_player(player.id)
    container.meetup_repository.save(meetup)
    return meetup


@pytest.fixture
def meetup_with_teams(bot_context):
    """Create and persist a meetup that already has teams with real players.

    Also seeds a tracked regular-group message so refresh_callup_messages can
    call edit_message_text during the lock callback test.
    """
    container = bot_context.bot_data["container"]
    settings = bot_context.bot_data["settings"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    p1 = Player.create("Alice", "regular")
    p2 = Player.create("Bob", "regular")
    container.player_repository.save(p1)
    container.player_repository.save(p2)
    meetup.set_teams([Team.create("A", [p1.id]), Team.create("B", [p2.id])])
    container.meetup_repository.save(meetup)
    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    store.save_message(meetup.date, "regular", MessageTracking(chat_id=-100111, message_id=1001))
    return meetup


@pytest.mark.asyncio
async def test_create_teams_callback_authorized_creates_teams(
    callback_update, bot_context, meetup_with_players  # pylint: disable=unused-argument
):
    """Admin pressing create_teams creates balanced teams and persists them."""
    bot_context.bot_data["settings"].telegram.is_authorized.return_value = True
    callback_update.callback_query.data = "create_teams:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup.teams is not None
    callback_update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_create_teams_callback_unauthorized_answers_admin_alert(
    callback_update, bot_context, saved_meetup  # pylint: disable=unused-argument
):
    """Non-admin pressing create_teams receives an admin-only alert."""
    bot_context.bot_data["settings"].telegram.is_authorized.return_value = False
    callback_update.callback_query.data = "create_teams:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    call_kwargs = callback_update.callback_query.answer.call_args
    assert call_kwargs[1].get("show_alert") is True
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "administrador" in text.lower()


@pytest.mark.asyncio
async def test_lock_callback_authorized_removes_buttons(
    callback_update, bot_context, meetup_with_teams  # pylint: disable=unused-argument
):
    """Admin pressing lock removes keyboards from all tracked messages."""
    bot_context.bot_data["settings"].telegram.is_authorized.return_value = True
    callback_update.callback_query.data = "lock:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    bot_context.bot.edit_message_text.assert_called()
    callback_update.callback_query.answer.assert_called_once()
    bot_context.bot.send_photo.assert_not_called()


@pytest.mark.asyncio
async def test_lock_callback_unauthorized_answers_admin_alert(
    callback_update, bot_context, saved_meetup  # pylint: disable=unused-argument
):
    """Non-admin pressing lock receives an admin-only alert."""
    bot_context.bot_data["settings"].telegram.is_authorized.return_value = False
    callback_update.callback_query.data = "lock:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    call_kwargs = callback_update.callback_query.answer.call_args
    assert call_kwargs[1].get("show_alert") is True
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "administrador" in text.lower()
