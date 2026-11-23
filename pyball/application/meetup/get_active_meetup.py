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

"""Get active meetup use case."""
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class GetActiveMeetup:
    """Use case for finding the current active meetup."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, require_teams: bool = False) -> Meetup:
        """Return the most recent active meetup, or raise MeetupNotFoundError.

        An active meetup has not been closed. If require_teams is True,
        only meetups with assigned teams are eligible.
        """
        all_meetups = self.meetup_repository.find_all()
        active = [m for m in all_meetups if not m.closed]
        if require_teams:
            active = [m for m in active if m.teams is not None]
        if not active:
            raise MeetupNotFoundError("active")
        return max(active, key=lambda m: m.date)
