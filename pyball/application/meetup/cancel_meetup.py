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
"""Cancel (delete) the active meetup use case."""

import logging

from pyball.domain.meetup.errors import MeetupLockedError, MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository

logger = logging.getLogger(__name__)


class CancelMeetup:
    """Use case for cancelling (deleting) the current active meetup."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self) -> Meetup:
        """Delete the most recent active meetup and return it.

        An active meetup has not been closed (same lookup as GetActiveMeetup).

        Returns:
            The deleted meetup.

        Raises:
            MeetupNotFoundError: No active meetup exists.
            MeetupLockedError: The active meetup is locked.
        """
        all_meetups = self.meetup_repository.find_all()
        active = [m for m in all_meetups if not m.closed]
        if not active:
            raise MeetupNotFoundError("active")
        meetup = max(active, key=lambda m: m.date)
        if meetup.locked:
            raise MeetupLockedError(f"Meetup at {meetup.date} is locked, cannot cancel.")
        self.meetup_repository.delete(meetup.id)
        logger.info("Meetup cancelled for %s", meetup.date)
        return meetup
