"""Tests for keeping the callups in step with PyBall's events."""

from datetime import datetime

import pytest

from pyball_telegram.api import Event
from pyball_telegram.state import TrackedMessage
from tests.conftest import DATE, meetup


def _event(kind, raw, **extra):
    return Event.model_validate({"id": 1, "type": kind, "meetup": raw} | extra)


@pytest.mark.asyncio
async def test_a_new_meetup_posts_the_regulars_callup_with_buttons(callups, bot):
    """meetup.created sends the callup to the regulars chat and tracks it."""
    await callups.handle(_event("meetup.created", meetup()))

    kwargs = bot.send_message.call_args.kwargs
    assert (kwargs["chat_id"], kwargs["message_thread_id"]) == (-10, 5)
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "join:2026-11-25T20:00"
    assert callups.messages.get(DATE, "regular") == TrackedMessage(-10, 100, 5)


@pytest.mark.asyncio
async def test_a_join_edits_both_callups(callups, bot):
    """player.joined edits the tracked messages; the subs buttons only while searching."""
    callups.messages.save(DATE, "regular", TrackedMessage(-10, 1))
    callups.messages.save(DATE, "substitute", TrackedMessage(-20, 2))

    await callups.handle(_event("player.joined", meetup(), is_substitute=False))

    regular, substitute = bot.edit_message_text.call_args_list
    assert regular.kwargs["message_id"] == 1 and regular.kwargs["reply_markup"] is not None
    assert substitute.kwargs["message_id"] == 2 and substitute.kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_a_closed_match_shows_the_summary_untracks_and_posts_stats(callups, bot, core):
    """match.closed edits in the core's summary, forgets the messages, posts the stats."""
    core.routes[("GET", "/api/v1/meetups/m1/summary")] = {"text": "*Blanco - 1*"}
    core.routes[("GET", "/api/v1/stats.png")] = b"png"
    callups.messages.save(DATE, "regular", TrackedMessage(-10, 1))

    await callups.handle(_event("match.closed", meetup(closed=True)))

    edit = bot.edit_message_text.call_args.kwargs
    assert edit["text"] == "*Blanco \\- 1*" and edit["reply_markup"] is None
    assert callups.messages.get(DATE, "regular") is None
    photo = bot.send_photo.call_args.kwargs
    assert (photo["chat_id"], photo["photo"], photo["message_thread_id"]) == (-30, b"png", 7)
    assert ("GET", "/api/v1/stats.png?scope=season") in core.calls


@pytest.mark.asyncio
async def test_a_cancelled_meetup_is_marked_and_forgotten(callups, bot):
    """meetup.cancelled prefixes CANCELADO and drops the buttons and the tracking."""
    callups.messages.save(DATE, "regular", TrackedMessage(-10, 1))

    await callups.handle(_event("meetup.cancelled", meetup()))

    edit = bot.edit_message_text.call_args.kwargs
    assert edit["text"].startswith("🚫 *CANCELADO*\n\n📅") and edit["reply_markup"] is None
    assert callups.messages.get(DATE, "regular") is None


@pytest.mark.asyncio
async def test_a_new_date_moves_the_tracking(callups, bot):
    """meetup.date_changed re-keys the messages and edits them with the new date."""
    callups.messages.save(DATE, "regular", TrackedMessage(-10, 1))
    later = datetime(2026, 11, 26, 21, 0)

    raw = meetup(date=later.isoformat())
    await callups.handle(_event("meetup.date_changed", raw, previous_date=DATE.isoformat()))

    assert callups.messages.get(later, "regular") == TrackedMessage(-10, 1)
    assert "2026-11-26 21:00" in bot.edit_message_text.call_args.kwargs["text"]


@pytest.mark.asyncio
async def test_an_opened_search_posts_the_substitutes_callup(callups, bot):
    """substitute_search.opened sends the substitutes callup with its buttons."""
    await callups.handle(_event("substitute_search.opened", meetup(substitute_search=True)))

    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == -20
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data.startswith("join_sub:")
    assert callups.messages.get(DATE, "substitute") == TrackedMessage(-20, 100)


@pytest.mark.asyncio
async def test_a_corrected_result_is_a_new_message(callups, bot, core):
    """match.edited posts the corrected summary and the stats again."""
    core.routes[("GET", "/api/v1/meetups/m1/summary")] = {"text": "Ana"}
    core.routes[("GET", "/api/v1/stats.png")] = b"png"

    await callups.handle(_event("match.edited", meetup(closed=True)))

    assert bot.send_message.call_args.kwargs["text"] == "✏️ Resultado corregido\n\nAna"
    bot.send_photo.assert_awaited_once()


@pytest.mark.asyncio
async def test_untracked_meetups_ask_nothing(callups, bot, core):
    """An update to a meetup with no message edits nothing and calls nothing."""
    await callups.handle(_event("meetup.updated", meetup()))
    bot.edit_message_text.assert_not_awaited()
    assert not core.calls
