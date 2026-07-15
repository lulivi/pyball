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
"""Destroy teams use case."""

from datetime import datetime

from pyball.domain.meetup.errors import (
    MeetupHasNoTeamsError,
    MeetupHasRecordedResultsError,
    MeetupNotFoundError,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class DestroyTeams:
    """Use case for discarding a meetup's teams and reopening signup."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, meetup_date: datetime) -> Meetup:
        """Clear the meetup's teams, matches, closed, and locked state.

        Raises:
            MeetupNotFoundError: No meetup exists at meetup_date.
            MeetupHasNoTeamsError: The meetup has no teams to destroy.
            MeetupHasRecordedResultsError: A match already has a recorded result.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.teams is None:
            raise MeetupHasNoTeamsError(f"Meetup at {meetup_date} has no teams to destroy.")
        if any(match.result is not None for match in meetup.matches):
            raise MeetupHasRecordedResultsError(
                f"Meetup at {meetup_date} already has a recorded match result."
            )

        meetup.clear_teams()
        self.meetup_repository.save(meetup)
        return meetup
