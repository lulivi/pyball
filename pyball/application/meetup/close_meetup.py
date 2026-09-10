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
"""Close meetup use case (explicit close for triangulars)."""

import logging
from datetime import datetime

from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository

logger = logging.getLogger(__name__)


class CloseMeetup:
    """Use case for explicitly closing a meetup (used to end a triangular session)."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, meetup_date: datetime) -> Meetup:
        """Close the meetup at the given date.

        Raises:
            MeetupNotFoundError: If no meetup exists at the date.
            MeetupAlreadyClosedError: If the meetup is already closed.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.is_closed():
            raise MeetupAlreadyClosedError(f"Meetup on {meetup_date} is already closed.")

        if meetup.matches and meetup.matches[-1].result is None:
            meetup.matches.pop()

        meetup.close()
        self.meetup_repository.save(meetup)
        logger.info("Meetup closed for %s", meetup_date)
        return meetup
