"""Tests for the admin commands."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pyball_telegram.commands import (
    help_command,
    link_command,
    setup_commands,
    short_alias,
    show_command,
    stats_command,
)
from pyball_telegram.state import LinkStore
from tests.conftest import LUIS, SUB, meetup


def _update(user_id=1, chat_id=-10):
    message = MagicMock(chat_id=chat_id, message_id=3, reply_text=AsyncMock())
    return MagicMock(message=message, effective_user=MagicMock(id=user_id)), message


def _context(callups, bot, *args):
    return MagicMock(bot_data={"callups": callups}, bot=bot, args=list(args))


def _guarded(handler):
    """The handler as registered, behind the admin check."""
    application = MagicMock()
    setup_commands(application)
    for call in application.add_handler.call_args_list:
        registered = call.args[0]
        if registered.callback.__name__ == handler.__name__:
            return registered.callback
    raise AssertionError(handler.__name__)


def test_aliases():
    """player_ and meetup_ commands get p_ and m_ aliases."""
    assert short_alias("player_link") == "p_link"
    assert short_alias("meetup_show") == "m_show"
    assert short_alias("help") is None


@pytest.mark.asyncio
async def test_help_lists_the_commands(callups, bot):
    """/help answers anyone with every command by category."""
    update, message = _update(user_id=99)
    await help_command(update, _context(callups, bot))
    assert "`/meetup_stats`" in message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_non_admins_are_refused(callups, bot, core):
    """An admin command from anyone else is refused before it does anything."""
    update, message = _update(user_id=99)
    await _guarded(link_command)(update, _context(callups, bot, "Luis,", "7"))
    assert "Unauthorized" in message.reply_text.call_args.args[0]
    assert not core.calls


@pytest.mark.asyncio
async def test_link_matches_the_name_fuzzily(callups, bot):
    """/player_link Lui, 7 links user 7 to Luis and reacts."""
    update, _ = _update()
    await _guarded(link_command)(update, _context(callups, bot, "Lui,", "7"))
    assert LinkStore(callups.config.mapping_file).player_id(7) == LUIS
    bot.set_message_reaction.assert_awaited_once()


@pytest.mark.asyncio
async def test_show_reposts_the_active_meetup_and_its_substitutes(callups, bot, core):
    """/meetup_show posts both callups when a substitute plays."""
    core.routes[("GET", "/api/v1/meetups/active")] = meetup(players=[LUIS, SUB])
    update, _ = _update()

    await _guarded(show_command)(update, _context(callups, bot))

    chats = [c.kwargs["chat_id"] for c in bot.send_message.call_args_list]
    assert chats == [-10, -20]


@pytest.mark.asyncio
async def test_show_without_an_active_meetup_says_so(callups, bot):
    """No active meetup: a reply, nothing posted."""
    update, message = _update()
    await _guarded(show_command)(update, _context(callups, bot))
    message.reply_text.assert_awaited_once_with("No hay ningún partido activo.")
    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_stats_in_the_stats_chat_go_to_its_topic(callups, bot, core):
    """/meetup_stats historico renders all-time stats in the stats topic."""
    core.routes[("GET", "/api/v1/stats.png")] = b"png"
    update, _ = _update(chat_id=-30)

    await _guarded(stats_command)(update, _context(callups, bot, "historico"))

    assert ("GET", "/api/v1/stats.png?scope=alltime") in core.calls
    photo = bot.send_photo.call_args.kwargs
    assert (photo["message_thread_id"], photo["caption"]) == (7, "📊 Histórico")
