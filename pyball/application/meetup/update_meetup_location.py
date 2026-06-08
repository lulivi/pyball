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
"""Update meetup location use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class UpdateMeetupLocation:
    """Use case for updating a meetup's location."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with a meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, meetup_date: datetime, new_location: str) -> Meetup:
        """Update the location of an existing meetup.

        Args:
            meetup_date: Date and time of the meetup to update.
            new_location: The new location for the meetup.

        Returns:
            The updated Meetup.

        Raises:
            MeetupNotFoundError: If no meetup exists at the given date.
            ValueError: If the new location is empty or blank.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        meetup.set_location(new_location)
        self.meetup_repository.save(meetup)
        return meetup
