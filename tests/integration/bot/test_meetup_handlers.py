"""Integration tests for meetup bot handlers."""

# pylint: disable=redefined-outer-name

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
import telegram

from pyball.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    list_meetups_handler,
    new_meetup_handler,
    next_meetup_handler,
    remove_player_handler,
    search_handler,
    show_meetup_handler,
    start_match_handler,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram import TelegramMessageStore


@pytest.mark.asyncio
async def test_new_meetup_persists(bot_update, bot_context):
    """Create a meetup and verify it exists in the real repo."""
    bot_context.args = ["2026/04/25", "20:00"]

    await new_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert meetup is not None
    assert meetup.location == "Test Field"


@pytest.mark.asyncio
async def test_new_meetup_duplicate_replies_error(bot_update, bot_context):
    """Reply with duplicate error when a meetup already exists on that date."""
    bot_context.args = ["2026/04/25", "20:00"]
    await new_meetup_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_meetup_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "already exists" in text


@pytest.mark.asyncio
async def test_add_player_updates_meetup(bot_update, bot_context):
    """Add a player via handler and verify the meetup in the real repo is updated."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await add_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id in saved.players


@pytest.mark.asyncio
async def test_remove_player_updates_meetup(bot_update, bot_context):
    """Remove a player via handler and verify the meetup in the real repo is updated."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await remove_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id not in saved.players


@pytest.mark.asyncio
async def test_create_teams_persists_teams(bot_update, bot_context):
    """Create teams via handler and verify teams are stored in the real repo."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"Player{i}", "regular") for i in range(4)]
    for player in players:
        container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for player in players:
        meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await create_teams_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert saved.teams is not None
    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "Equipos creados" in text


@pytest.mark.asyncio
async def test_list_meetups_shows_date(bot_update, bot_context):
    """List meetups and verify the reply includes the date of a saved meetup."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    await list_meetups_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "2026/04/25" in text


@pytest.mark.asyncio
async def test_show_meetup_includes_player_name(bot_update, bot_context):
    """Show a meetup and verify the reply includes a player name from the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "Luis" in text


@pytest.mark.asyncio
async def test_start_match_forbidden_admin_does_not_raise(bot_update, bot_context):
    """Catch Forbidden per admin in start_match without re-raising."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"P{i}", "regular") for i in range(4)]
    for player in players:
        container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for player in players:
        meetup.add_player(player.id)
    meetup.create_random_teams()
    container.meetup_repository.save(meetup)

    bot_context.bot.send_message = AsyncMock(
        side_effect=telegram.error.Forbidden("bot was blocked by the user")
    )
    bot_context.args = ["2026/04/25", "20:00"]

    await start_match_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    bot_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_next_meetup_creates_meetup(bot_update, bot_context):
    """next_meetup_handler creates a meetup for the next default weekday."""
    await next_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetups = container.meetup_repository.find_all()
    assert len(meetups) == 1
    first_call_text = bot_update.message.reply_text.call_args_list[0][0][0]
    assert "Creating meetup for" in first_call_text


@pytest.mark.asyncio
async def test_search_handler_sends_and_stores(bot_update, bot_context):
    """search_handler sends the substitutes message and persists tracking to the store."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25"]

    await search_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    settings = bot_context.bot_data["settings"]
    store = TelegramMessageStore(settings.paths.bot_messages_file)
    tracking = store.get_message("2026-04-25T20:00", "substitute")
    assert tracking is not None
    assert tracking.message_id == 42


@pytest.mark.asyncio
async def test_add_player_partial_failure(bot_update, bot_context):
    """add_player_handler with one valid name and one unknown name replies with Added and Failed."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis,", "Ghost"]

    await add_player_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "Added: Luis" in text
    assert "Failed:" in text


@pytest.mark.asyncio
async def test_show_meetup_no_players(bot_update, bot_context):
    """show_meetup_handler for a meetup with no players replies with 'No players yet.'"""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "No players yet." in text
