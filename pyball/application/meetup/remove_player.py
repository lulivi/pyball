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
"""Remove player from meetup use case."""

from datetime import datetime

from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


class RemovePlayerFromMeetup:
    """Use case for removing a player from a meetup."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ):
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self, meetup_date: datetime, player_name: str) -> Meetup:
        """Remove a player from a meetup by datetime and player name."""
        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if not meetup:
            raise MeetupNotFoundError(str(meetup_date))

        all_players = self.player_repository.find_all()
        match = fuzzy_match_player(player_name, all_players)

        meetup.remove_player(match.player_id)

        if meetup.teams is not None:
            meetup.clear_teams()

        self.meetup_repository.save(meetup)
        return meetup
