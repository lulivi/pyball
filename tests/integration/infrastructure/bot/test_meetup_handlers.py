"""Integration tests for meetup bot handlers."""

# pylint: disable=redefined-outer-name

from datetime import datetime

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
from pyball.infrastructure.telegram.bot.handlers.meetup import search_handler, stats_handler


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
async def test_stats_handler_bad_arg_replies_help(bot_update, bot_context):
    """stats_handler with an unknown arg replies with a help message."""
    bot_context.args = ["unknown"]
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_text.assert_called_once()
    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "temporada" in text and "historico" in text
