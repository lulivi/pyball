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
"""Notifier interface for match lifecycle events."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player

logger = logging.getLogger(__name__)


class MatchNotifier(ABC):
    """Abstract notifier called after match and meetup state changes."""

    @abstractmethod
    async def on_meetup_created(self, meetup: Meetup) -> None:
        """Handle a brand-new meetup by announcing it to the platform."""

    @abstractmethod
    async def on_match_closed(self, meetup: Meetup) -> None:
        """Handle a closed match by notifying the platform."""

    @abstractmethod
    async def on_meetup_updated(self, meetup: Meetup) -> None:
        """Handle a meetup update by refreshing platform messages."""

    @abstractmethod
    async def on_meetup_date_changed(self, old_date: datetime, meetup: Meetup) -> None:
        """Handle a meetup date change by re-keying and refreshing platform messages."""

    @abstractmethod
    async def on_match_edited(self, meetup: Meetup) -> None:
        """Handle a corrected match result by re-announcing it."""

    @abstractmethod
    async def on_meetup_cancelled(self, meetup: Meetup) -> None:
        """Handle a cancelled meetup by editing platform messages to show cancellation."""

    @abstractmethod
    async def on_substitute_search_opened(self, meetup: Meetup) -> None:
        """Handle an opened substitute search by calling for substitutes."""

    @abstractmethod
    async def on_player_joined(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Handle a player joining a meetup by notifying the activity feed."""

    @abstractmethod
    async def on_player_left(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Handle a player leaving a meetup by notifying the activity feed."""


class CompositeMatchNotifier(MatchNotifier):
    """Forwards every event to several notifiers in order; one failing never skips the rest."""

    def __init__(self, notifiers: list[MatchNotifier]) -> None:
        """Initialize with the notifiers to call, in order."""
        self._notifiers = notifiers

    async def on_meetup_created(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_meetup_created", meetup)

    async def on_match_closed(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_match_closed", meetup)

    async def on_meetup_updated(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_meetup_updated", meetup)

    async def on_meetup_date_changed(self, old_date: datetime, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_meetup_date_changed", old_date, meetup)

    async def on_match_edited(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_match_edited", meetup)

    async def on_meetup_cancelled(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_meetup_cancelled", meetup)

    async def on_substitute_search_opened(self, meetup: Meetup) -> None:
        """Forward to every notifier."""
        await self._each("on_substitute_search_opened", meetup)

    async def on_player_joined(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Forward to every notifier."""
        await self._each("on_player_joined", meetup, player, is_substitute)

    async def on_player_left(self, meetup: Meetup, player: Player, is_substitute: bool) -> None:
        """Forward to every notifier."""
        await self._each("on_player_left", meetup, player, is_substitute)

    async def _each(self, hook: str, *args) -> None:
        for notifier in self._notifiers:
            try:
                await getattr(notifier, hook)(*args)
            except Exception:  # pylint: disable=broad-except
                logger.exception("%s failed in %s", hook, type(notifier).__name__)
