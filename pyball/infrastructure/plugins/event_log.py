# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Persistent, ordered event log and the notifier that writes to it."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player
from pyball.infrastructure.plugins.schemas import EventOut, meetup_out, player_out


class EventLog:
    """Append-only JSONL log of events with increasing ids, plus live subscribers.

    Every event is kept forever and in memory: a club produces a handful per day.
    """

    def __init__(self, path: Path) -> None:
        """Load the existing events from ``path``, creating its directory if needed."""
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict[str, Any]] = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self._events = [json.loads(line) for line in f if line.strip()]
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    @property
    def last_id(self) -> int:
        """Return the id of the latest event, 0 when there is none."""
        return self._events[-1]["id"] if self._events else 0

    def append(self, event_type: str, meetup: Meetup, **extra: Any) -> dict[str, Any]:
        """Persist a new event about ``meetup`` and hand it to every live subscriber."""
        event = EventOut(
            id=self.last_id + 1,
            type=event_type,
            occurred_at=datetime.now().astimezone(),
            meetup=meetup_out(meetup),
            **extra,
        ).model_dump(mode="json", exclude_unset=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._events.append(event)
        for queue in self._subscribers:
            queue.put_nowait(event)
        return event

    def after(self, event_id: int, up_to: int | None = None) -> list[dict[str, Any]]:
        """Return the events with an id above ``event_id`` (and at most ``up_to``)."""
        last = self.last_id if up_to is None else up_to
        return [e for e in self._events if event_id < e["id"] <= last]

    def subscribe(self) -> tuple[int, asyncio.Queue[dict[str, Any]]]:
        """Start receiving new events; return the last id already in the log and the queue.

        Replaying ``after(seen, up_to=last_id)`` and then draining the queue yields
        every event exactly once, since no event can be appended between the two.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return self.last_id, queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Stop sending events to ``queue``."""
        self._subscribers.discard(queue)

    def search_open(self, meetup: Meetup) -> bool:
        """Return whether the latest event about ``meetup`` saw its substitute search open."""
        meetup_id = str(meetup.id.value)
        for event in reversed(self._events):
            if event["meetup"]["id"] == meetup_id:
                return event["meetup"]["substitute_search"]
        return False


class EventLogNotifier(MatchNotifier):
    """Records every MatchNotifier event in the event log.

    A substitute search closes as a side effect of joins, capacity changes and teams;
    whenever a meetup's search turns from open to closed, a substitute_search.closed
    event follows the event that closed it.
    """

    def __init__(self, log: EventLog) -> None:
        """Initialize with the event log to write to."""
        self._log = log

    async def on_meetup_created(self, meetup: Meetup) -> None:
        """Record meetup.created."""
        self._record("meetup.created", meetup)

    async def on_match_closed(self, meetup: Meetup) -> None:
        """Record match.closed."""
        self._record("match.closed", meetup)

    async def on_meetup_updated(self, meetup: Meetup) -> None:
        """Record meetup.updated."""
        self._record("meetup.updated", meetup)

    async def on_meetup_date_changed(self, old_date: datetime, meetup: Meetup) -> None:
        """Record meetup.date_changed with the previous date."""
        self._record("meetup.date_changed", meetup, previous_date=old_date)

    async def on_match_edited(self, meetup: Meetup) -> None:
        """Record match.edited."""
        self._record("match.edited", meetup)

    async def on_meetup_cancelled(self, meetup: Meetup) -> None:
        """Record meetup.cancelled."""
        self._record("meetup.cancelled", meetup)

    async def on_substitute_search_opened(self, meetup: Meetup) -> None:
        """Record substitute_search.opened."""
        self._log.append("substitute_search.opened", meetup)

    async def on_player_joined(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Record player.joined with the player."""
        self._record(
            "player.joined", meetup, player=player_out(player), is_substitute=is_substitute
        )

    async def on_player_left(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Record player.left with the player."""
        self._record("player.left", meetup, player=player_out(player), is_substitute=is_substitute)

    def _record(self, event_type: str, meetup: Meetup, **extra: Any) -> None:
        was_open = self._log.search_open(meetup)
        self._log.append(event_type, meetup, **extra)
        if was_open and not meetup.substitute_search:
            self._log.append("substitute_search.closed", meetup)
