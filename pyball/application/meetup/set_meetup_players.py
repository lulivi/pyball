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
"""Set meetup players use case."""

import logging
from datetime import datetime

from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupLockedError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId

logger = logging.getLogger(__name__)


class SetMeetupPlayers:
    """Use case for creating or resetting a meetup with a fixed player list."""

    def __init__(self, meetup_repository: MeetupRepository, default_location: str):
        """Initialize with the meetup repository and the default location."""
        self.meetup_repository = meetup_repository
        self.default_location = default_location

    def execute(self, date: datetime, player_ids: list[str]) -> Meetup:
        """Create or reset the meetup at ``date`` with exactly the given players.

        Args:
            date: Date and time of the meetup.
            player_ids: Player UUIDs (as strings) that form the new player list.

        Returns:
            The created or updated Meetup.

        Raises:
            MeetupAlreadyClosedError: If the existing meetup already has a result.
            MeetupLockedError: If the existing meetup is locked.
            InvalidPlayerIdError: If any player id is malformed.
        """
        ids = [PlayerId.from_string(pid) for pid in player_ids]
        meetup = self.meetup_repository.find_by_datetime(date)
        if meetup is not None and meetup.is_closed():
            raise MeetupAlreadyClosedError("Match already finished, cannot reset")
        created = meetup is None
        if meetup is None:
            meetup = Meetup.create(date=date, location=self.default_location)
        else:
            if meetup.locked:
                raise MeetupLockedError(f"Meetup at {date} is locked, cannot reset the roster.")
            meetup.players.clear()
            meetup.clear_teams()
        for pid in ids:
            meetup.add_player(pid)
        self.meetup_repository.save(meetup)
        if created:
            logger.info("Meetup created for %s with %d players", date, len(meetup.players))
        else:
            logger.debug("Meetup roster set for %s: %d players", date, len(meetup.players))
        return meetup
