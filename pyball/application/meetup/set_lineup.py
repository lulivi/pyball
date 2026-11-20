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
"""Set lineup use case: a meetup's final roster and, optionally, its teams, in one step."""

from datetime import datetime

from pyball.application.meetup.create_teams import CreateTeams
from pyball.domain.meetup.errors import (
    MeetupAlreadyClosedError,
    MeetupHasRecordedResultsError,
    MeetupNotFoundError,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class SetLineup:
    """Use case for replacing a meetup's roster and building its teams with one save."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        default_capacity: int,
        create_teams: CreateTeams | None,
    ) -> None:
        """Initialize; without ``create_teams`` the lineup leaves the meetup without teams."""
        self.meetup_repository = meetup_repository
        self.default_capacity = default_capacity
        self.create_teams = create_teams

    def execute(
        self, meetup_date: datetime, player_ids: list[PlayerId], team_count: int = 2
    ) -> Meetup:
        """Replace the roster, then build teams if asked; nothing is saved on error.

        Raises:
            MeetupNotFoundError: No meetup exists at meetup_date.
            MeetupAlreadyClosedError: The meetup is closed.
            MeetupHasRecordedResultsError: A match already has a recorded result.
            ValueError: Too few players or a team_count other than 2 or 3.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.is_closed():
            raise MeetupAlreadyClosedError("Match already finished, cannot change the lineup")
        if meetup.has_recorded_results():
            raise MeetupHasRecordedResultsError(
                f"Meetup at {meetup_date} already has a recorded result."
            )
        meetup.clear_teams()
        meetup.replace_players(player_ids, self.default_capacity)
        if self.create_teams is not None:
            self.create_teams.build(meetup, team_count)
        self.meetup_repository.save(meetup)
        return meetup
