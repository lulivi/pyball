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
"""Create meetup use case."""

from datetime import datetime

from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.exceptions import MeetupError


class CreateMeetup:
    """Use case for creating a new meetup."""

    def __init__(
        self, meetup_repository: MeetupRepository, default_location: str = "Parque Central"
    ):
        """Initialize CreateMeetup use case.

        Args:
            meetup_repository: Repository for persist meetups.
            default_location: Default location for new meetups.
        """
        self.meetup_repository = meetup_repository
        self.default_location = default_location

    def execute(self, date: datetime, location: str | None = None) -> Meetup:
        """Create a new meetup.

        Args:
            date: Date and time of the meetup.
            location: Optional location (defaults to self.default_location).

        Returns:
            The newly created Meetup.

        Raises:
            DuplicateMeetupError: If a meetup already exists at the given date.
        """
        if self.meetup_repository.find_by_date(date.date()) is not None:
            raise DuplicateMeetupError("Meetup already exists at this time")

        meetup = Meetup.create(date=date, location=location or self.default_location)
        self.meetup_repository.save(meetup)
        return meetup


class DuplicateMeetupError(MeetupError):
    """Raised when trying to create a meetup at a time that already exists."""
