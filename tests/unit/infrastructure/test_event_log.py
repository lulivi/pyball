"""Tests for the plugin event log and its notifier."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.plugins.event_log import EventLog, EventLogNotifier

DATE = datetime(2026, 7, 15, 20, 0)
_COLORS = ("blanco", "negro", "rojo")
_EMOJIS = ("⚪", "⚫", "🔴")


def _types(log: EventLog) -> list[str]:
    return [e["type"] for e in log.after(0)]


def test_ids_increase_and_survive_a_reload(tmp_path):
    """Events get consecutive ids and are read back in order after a restart."""
    log = EventLog(tmp_path / "events.jsonl", _COLORS, _EMOJIS)
    meetup = Meetup.create(DATE, "Campo")
    log.append("meetup.created", meetup)
    log.append("meetup.updated", meetup)

    reloaded = EventLog(tmp_path / "events.jsonl", _COLORS, _EMOJIS)

    assert [e["id"] for e in reloaded.after(0)] == [1, 2]
    assert reloaded.after(1)[0]["type"] == "meetup.updated"
    first = reloaded.after(0)[0]
    assert first["meetup"]["capacity"] == 10
    assert first["meetup"]["teams"] is None
    assert "player" not in first


def test_subscriber_gets_every_event_once_across_replay(tmp_path):
    """Replay up to the subscribe point, then the queue: no gap, no duplicate."""
    log = EventLog(tmp_path / "events.jsonl", _COLORS, _EMOJIS)
    meetup = Meetup.create(DATE, "Campo")
    for _ in range(3):
        log.append("meetup.updated", meetup)

    last_id, queue = log.subscribe()
    log.append("meetup.updated", meetup)  # lands while the replay is being sent
    seen = [e["id"] for e in log.after(1, up_to=last_id)]
    while not queue.empty():
        seen.append(queue.get_nowait()["id"])

    assert seen == [2, 3, 4]


@pytest.mark.asyncio
async def test_notifier_records_a_join_with_its_player(tmp_path):
    """player.joined carries the player and whether they joined as a substitute."""
    log = EventLog(tmp_path / "events.jsonl", _COLORS, _EMOJIS)
    meetup = Meetup.create(DATE, "Campo")
    player = Player.create("Ana", "substitute")

    await EventLogNotifier(log).on_player_joined(meetup, player, True)

    event = log.after(0)[0]
    assert (event["type"], event["player"]["name"], event["is_substitute"]) == (
        "player.joined",
        "Ana",
        True,
    )


@pytest.mark.asyncio
async def test_notifier_follows_the_closing_event_with_search_closed(tmp_path):
    """The join that fills the roster is followed by substitute_search.closed."""
    log = EventLog(tmp_path / "events.jsonl", _COLORS, _EMOJIS)
    notifier = EventLogNotifier(log)
    meetup = Meetup.create(DATE, "Campo", capacity=2)
    meetup.add_player(PlayerId.generate())
    meetup.open_substitute_search()
    await notifier.on_substitute_search_opened(meetup)

    player = Player.create("Ana")
    meetup.add_player(player.id)
    await notifier.on_player_joined(meetup, player, False)
    await notifier.on_meetup_updated(meetup)

    assert _types(log) == [
        "substitute_search.opened",
        "player.joined",
        "substitute_search.closed",
        "meetup.updated",
    ]


@pytest.mark.asyncio
async def test_search_state_survives_a_restart(tmp_path):
    """After a restart the log still knows the search was open."""
    meetup = Meetup.create(DATE, "Campo", capacity=2)
    meetup.open_substitute_search()
    await EventLogNotifier(
        EventLog(tmp_path / "e.jsonl", _COLORS, _EMOJIS)
    ).on_substitute_search_opened(meetup)

    log = EventLog(tmp_path / "e.jsonl", _COLORS, _EMOJIS)
    meetup.close_substitute_search()
    await EventLogNotifier(log).on_meetup_updated(meetup)

    assert _types(log)[-1] == "substitute_search.closed"


def test_a_line_torn_by_a_crash_is_dropped(tmp_path):
    """A half-written last line is discarded, and the next event follows the last whole one."""
    path = tmp_path / "events.jsonl"
    log = EventLog(path, _COLORS, _EMOJIS)
    meetup = Meetup.create(DATE, "Campo")
    log.append("meetup.created", meetup)
    with open(path, "a", encoding="utf-8") as f:
        f.write('{"id": 2, "type": "meetup.upd')

    reloaded = EventLog(path, _COLORS, _EMOJIS)
    reloaded.append("meetup.updated", meetup)

    assert [e["id"] for e in EventLog(path, _COLORS, _EMOJIS).after(0)] == [1, 2]
