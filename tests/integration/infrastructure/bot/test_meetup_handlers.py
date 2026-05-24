"""Integration tests for meetup bot handlers."""

# pylint: disable=redefined-outer-name

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import telegram

from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    list_meetups_handler,
    new_meetup_handler,
    next_meetup_handler,
    remove_player_handler,
    search_handler,
    show_meetup_handler,
    start_match_handler,
    stats_handler,
)


@pytest.mark.asyncio
async def test_new_meetup_persists(bot_update, bot_context):
    """Create a meetup and verify it exists in the real repo."""
    bot_context.args = ["2026-04-25", "20:00"]

    await new_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert meetup is not None
    assert meetup.location == "Test Field"


@pytest.mark.asyncio
async def test_new_meetup_duplicate_replies_error(bot_update, bot_context):
    """Reply with duplicate error when a meetup already exists on that date."""
    bot_context.args = ["2026-04-25", "20:00"]
    await new_meetup_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_meetup_handler(bot_update, bot_context)

    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "ya existe" in text.lower()


@pytest.mark.asyncio
async def test_add_player_updates_meetup(bot_update, bot_context):
    """Add a player via handler and verify the meetup in the real repo is updated."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026-04-25", "20:00", "Luis"]

    await add_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
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

    bot_context.args = ["2026-04-25", "20:00", "Luis"]

    await remove_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
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

    bot_context.args = ["2026-04-25", "20:00"]

    await create_teams_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert saved.teams is not None
    bot_context.bot.set_message_reaction.assert_called_once()
    bot_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_list_meetups_shows_date(bot_update, bot_context):
    """List meetups and verify the reply includes the date of a saved meetup."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    await list_meetups_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "2026-04-25" in text


@pytest.mark.asyncio
async def test_show_meetup_includes_player_name(bot_update, bot_context):
    """Show a meetup and verify the reply includes a player name from the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026-04-25", "20:00"]

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
    meetup.set_teams(
        [
            Team.create("A", [players[0].id, players[1].id]),
            Team.create("B", [players[2].id, players[3].id]),
        ]
    )
    container.meetup_repository.save(meetup)

    bot_context.bot.send_photo = AsyncMock(
        side_effect=telegram.error.Forbidden("bot was blocked by the user")
    )
    bot_context.args = ["2026-04-25", "20:00"]

    await start_match_handler(bot_update, bot_context)

    bot_context.bot.send_photo.assert_called_once()
    bot_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_next_meetup_creates_meetup(bot_update, bot_context):
    """next_meetup_handler creates a meetup for the next default weekday."""
    await next_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetups = container.meetup_repository.find_all()
    assert len(meetups) == 1
    bot_update.message.reply_text.assert_not_called()
    bot_context.bot.set_message_reaction.assert_called_once()


@pytest.mark.asyncio
async def test_search_handler_sends_and_stores(bot_update, bot_context):
    """search_handler sends the substitutes message and persists tracking to the store."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026-04-25", "20:00"]

    await search_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    settings = bot_context.bot_data["settings"]
    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    tracking = store.get_message(datetime(2026, 4, 25, 20, 0), "substitute")
    assert tracking is not None
    assert tracking.message_id == 42


@pytest.mark.asyncio
async def test_add_player_partial_failure(bot_update, bot_context):
    """add_player_handler with one valid name and one unknown name replies w/ Added and Failed."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026-04-25", "20:00", "Luis,", "Ghost"]

    await add_player_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "Fallidos:" in text
    assert "Ghost" in text
    assert "Añadidos" not in text


@pytest.mark.asyncio
async def test_show_meetup_no_players(bot_update, bot_context):
    """show_meetup_handler for a meetup with no players replies with 'No players yet.'"""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026-04-25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "*Jugadores \\(0/10\\):*" in text


@pytest.mark.asyncio
async def test_stats_handler_temporada_sends_photo(bot_update, bot_context, monkeypatch):
    """stats_handler with 'temporada' sends one photo with season caption."""
    fake_png = b"\x89PNG\r\n\x1a\n"
    captured = {}

    async def fake_render(_self, _report, scope="season"):
        captured["scope"] = scope
        return fake_png

    monkeypatch.setattr(StatsHtmlRenderer, "render", fake_render)
    bot_context.args = ["temporada"]
    await stats_handler(bot_update, bot_context)
    bot_context.bot.send_photo.assert_called_once()
    assert captured["scope"] == "season"
    kwargs = bot_context.bot.send_photo.call_args.kwargs
    assert kwargs["photo"] == fake_png
    assert "Esta temporada" in kwargs["caption"]


@pytest.mark.asyncio
async def test_stats_handler_historico_sends_photo(bot_update, bot_context, monkeypatch):
    """stats_handler with 'historico' sends one photo with all-time caption."""
    fake_png = b"\x89PNG\r\n\x1a\n"
    captured = {}

    async def fake_render(_self, _report, scope="season"):
        captured["scope"] = scope
        return fake_png

    monkeypatch.setattr(StatsHtmlRenderer, "render", fake_render)
    bot_context.args = ["historico"]
    await stats_handler(bot_update, bot_context)
    bot_context.bot.send_photo.assert_called_once()
    assert captured["scope"] == "alltime"
    kwargs = bot_context.bot.send_photo.call_args.kwargs
    assert "Histórico" in kwargs["caption"]


@pytest.mark.asyncio
async def test_stats_handler_no_args_replies_help(bot_update, bot_context):
    """stats_handler with no args replies with a help message."""
    bot_context.args = []
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_text.assert_called_once()
    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "temporada" in text and "historico" in text


@pytest.mark.asyncio
async def test_create_teams_manual_persists_teams(bot_update, bot_context):
    """manual mode assigns named players to teams and persists them."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"Player{i}", "regular") for i in range(4)]
    for player in players:
        container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for player in players:
        meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = [
        "2026-04-25",
        "20:00",
        "manual",
        "Player0,",
        "Player1",
        ";",
        "Player2,",
        "Player3",
    ]

    await create_teams_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_datetime(datetime(2026, 4, 25, 20, 0))
    assert saved.teams is not None
    assert len(saved.teams) == 2
    bot_context.bot.set_message_reaction.assert_called_once()
    bot_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_create_teams_manual_unknown_player_replies_error(bot_update, bot_context):
    """manual mode with an unknown player name replies with an error message."""
    container = bot_context.bot_data["container"]
    player = Player.create("Player0", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = [
        "2026-04-25",
        "20:00",
        "manual",
        "Player0",
        ";",
        "Ghost",
    ]

    await create_teams_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "no encontrados" in text.lower()


@pytest.mark.asyncio
async def test_stats_handler_bad_arg_replies_help(bot_update, bot_context):
    """stats_handler with an unknown arg replies with a help message."""
    bot_context.args = ["unknown"]
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_text.assert_called_once()
    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "temporada" in text and "historico" in text
