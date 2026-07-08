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
"""Start next round use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupHasNoTeamsError, MeetupNotFoundError
from pyball.domain.meetup.models import Match, Meetup
from pyball.domain.meetup.next_round_calculator import pick_first_pairing
from pyball.domain.meetup.repository import MeetupRepository


class StartNextRound:
    """Use case that ensures a meetup has a pending match ready for tracking."""

    def __init__(self, meetup_repository: MeetupRepository):
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, meetup_date: datetime) -> Meetup:
        """Return the meetup with a pending match ready for tracking.

        If a match is already pending (no result yet), this is a no-op. Otherwise,
        creates the first match: the 2 teams for classic meetups, or a random pairing
        of 2 of the 3 teams for triangulars.

        Raises:
            MeetupNotFoundError: If no meetup exists at the date.
            MeetupHasNoTeamsError: If the meetup has no teams assigned.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")

        if meetup.current_match() is None and not meetup.matches:
            teams = meetup.teams
            if len(teams) == 2:
                pairing = (teams[0], teams[1])
            else:
                pairing = pick_first_pairing((teams[0], teams[1], teams[2]))
            meetup.add_match(Match(teams_playing=pairing))
            self.meetup_repository.save(meetup)

        return meetup
