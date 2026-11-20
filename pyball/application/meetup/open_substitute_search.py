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
"""Open substitute search use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class OpenSubstituteSearch:
    """Use case for starting to look for substitutes for a meetup."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, meetup_date: datetime) -> Meetup:
        """Open the substitute search of the meetup at meetup_date.

        Raises:
            MeetupNotFoundError: No meetup exists at meetup_date.
            SignupClosedError: The meetup already has teams.
            MeetupFullError: The roster already reached the capacity.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        meetup.open_substitute_search()
        self.meetup_repository.save(meetup)
        return meetup
