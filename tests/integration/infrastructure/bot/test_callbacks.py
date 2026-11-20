"""Integration tests for the inline callback handler."""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import CallbackQuery, Message, Update, User

from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.bot.callbacks import callback_handler
from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.infrastructure.telegram.message_store import MessageTracking

# pylint: disable=redefined-outer-name


def _open_search(bot_context, meetup, capacity):
    """Open a substitute search for ``capacity`` players, tracked as subs message 7."""
    meetup.capacity = capacity
    meetup.open_substitute_search()
    bot_context.bot_data["container"].meetup_repository.save(meetup)
    settings = bot_context.bot_data["settings"]
    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    store.save_message(
        datetime(2026, 4, 25, 20, 0),
        "substitute",
        MessageTracking(chat_id=-100222, message_id=7),
    )


def _stored(bot_context):
    container = bot_context.bot_data["container"]
    return container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))


def _fill(bot_context, meetup, n):
    container = bot_context.bot_data["container"]
    for _ in range(n):
        meetup.add_player(PlayerId.generate())
    container.meetup_repository.save(meetup)


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
async def test_join_notifies_player_joined_as_titular(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Join callback notifies on_player_joined with is_substitute=False."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    notifier = bot_context.bot_data["notifier"]
    notifier.on_player_joined.assert_called_once()
    args = notifier.on_player_joined.call_args.args
    assert args[1].name == linked_player.name
    assert args[2] is False


@pytest.mark.asyncio
async def test_join_sub_notifies_player_joined_as_suplente(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Join-sub callback notifies on_player_joined with is_substitute=True."""
    _open_search(bot_context, saved_meetup, 10)
    callback_update.callback_query.data = "join_sub:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    notifier = bot_context.bot_data["notifier"]
    notifier.on_player_joined.assert_called_once()
    assert notifier.on_player_joined.call_args.args[2] is True


@pytest.mark.asyncio
async def test_leave_notifies_player_left_as_titular(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Leave callback notifies on_player_left with is_substitute=False."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)
    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    notifier = bot_context.bot_data["notifier"]
    notifier.on_player_left.assert_called_once()
    assert notifier.on_player_left.call_args.args[2] is False


@pytest.mark.asyncio
async def test_leave_sub_notifies_player_left_as_suplente(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Leave-sub callback notifies on_player_left with is_substitute=True."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)
    callback_update.callback_query.data = "leave_sub:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    notifier = bot_context.bot_data["notifier"]
    notifier.on_player_left.assert_called_once()
    assert notifier.on_player_left.call_args.args[2] is True


@pytest.mark.asyncio
async def test_join_duplicate_does_not_notify(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Rejecting an already-joined player never calls the notifier."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    notifier = bot_context.bot_data["notifier"]
    notifier.on_player_joined.assert_not_called()


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
async def test_join_signup_closed_when_teams_exist(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Join callback rejects and leaves teams untouched once teams already exist."""
    container = bot_context.bot_data["container"]
    extra_id = PlayerId.generate()
    saved_meetup.add_player(extra_id)
    saved_meetup.set_teams([Team.create("A", [extra_id]), Team.create("B", [])])
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup.teams is not None
    assert linked_player.id not in meetup.players
    call_kwargs = callback_update.callback_query.answer.call_args
    assert call_kwargs[1].get("show_alert") is True
    text = call_kwargs[1].get("text") or call_kwargs[0][0]
    assert "equipos" in text.lower()


@pytest.mark.asyncio
async def test_leave_signup_closed_when_teams_exist(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Leave callback rejects and leaves teams untouched once teams already exist."""
    container = bot_context.bot_data["container"]
    extra_id = PlayerId.generate()
    saved_meetup.add_player(linked_player.id)
    saved_meetup.add_player(extra_id)
    saved_meetup.set_teams([Team.create("A", [linked_player.id]), Team.create("B", [extra_id])])
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup.teams is not None
    assert linked_player.id in meetup.players
    call_kwargs = callback_update.callback_query.answer.call_args
    assert call_kwargs[1].get("show_alert") is True


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
async def test_join_logs_debug_event(
    callback_update,
    bot_context,
    linked_player,  # pylint: disable=unused-argument
    saved_meetup,  # pylint: disable=unused-argument
    caplog,
):
    """Join callback logs a DEBUG event with player name."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    with caplog.at_level(logging.DEBUG, logger="pyball.infrastructure.telegram.bot.callbacks"):
        await callback_handler(callback_update, bot_context)

    join_records = [
        r for r in caplog.records if "joined" in r.message.lower() or "luis" in r.message.lower()
    ]
    assert join_records and all(r.levelno == logging.DEBUG for r in join_records)


@pytest.mark.asyncio
async def test_leave_logs_debug_event(
    callback_update,
    bot_context,
    linked_player,
    saved_meetup,
    caplog,
):
    """Leave callback logs a DEBUG event with player name."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    with caplog.at_level(logging.DEBUG, logger="pyball.infrastructure.telegram.bot.callbacks"):
        await callback_handler(callback_update, bot_context)

    leave_records = [
        r for r in caplog.records if "left" in r.message.lower() or "luis" in r.message.lower()
    ]
    assert leave_records and all(r.levelno == logging.DEBUG for r in leave_records)


@pytest.mark.asyncio
async def test_join_sub_rejected_when_no_search_open(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """Without an open search a substitute cannot join."""
    callback_update.callback_query.data = "join_sub:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert linked_player.id not in meetup.players
    callback_update.callback_query.answer.assert_called_once_with(
        "La búsqueda de suplentes está cerrada.", show_alert=True
    )


@pytest.mark.asyncio
async def test_join_sub_rejected_when_target_reached(
    callback_update, bot_context, linked_player, saved_meetup
):
    """A stale open target already reached by the roster still blocks joins."""
    _open_search(bot_context, saved_meetup, 10)
    _fill(bot_context, saved_meetup, 10)
    callback_update.callback_query.data = "join_sub:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert linked_player.id not in meetup.players


@pytest.mark.asyncio
async def test_regular_join_reaching_target_closes_search(
    callback_update, bot_context, linked_player, saved_meetup  # pylint: disable=unused-argument
):
    """The 10th player (a regular) closes the search and strips the subs keyboard."""
    _open_search(bot_context, saved_meetup, 10)
    _fill(bot_context, saved_meetup, 9)
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    assert not _stored(bot_context).substitute_search
    subs_edit = next(
        c for c in bot_context.bot.edit_message_text.call_args_list if c.kwargs["message_id"] == 7
    )
    assert subs_edit.kwargs["reply_markup"] is None
    assert "Completo" in subs_edit.kwargs["text"]


@pytest.mark.asyncio
async def test_leave_from_eleven_closes_search_at_ten(
    callback_update, bot_context, linked_player, saved_meetup
):
    """Searching for 12 with 11 players: a leave lands on 10 and completes the search."""
    _open_search(bot_context, saved_meetup, 12)
    _fill(bot_context, saved_meetup, 10)
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)
    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    assert not _stored(bot_context).substitute_search
    assert _stored(bot_context).capacity == 10
