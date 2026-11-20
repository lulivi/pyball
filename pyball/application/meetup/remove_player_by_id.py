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
"""Remove player from meetup by ID use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError, SignupClosedError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class RemovePlayerFromMeetupById:
    """Use case for removing an already-identified player from a meetup."""

    def __init__(self, meetup_repository: MeetupRepository, default_capacity: int):
        """Initialize the use case with the meetup repository and the club's capacity."""
        self.meetup_repository = meetup_repository
        self.default_capacity = default_capacity

    def execute(self, meetup_date: datetime, player_id: PlayerId) -> Meetup:
        """Remove a player from a meetup by datetime and an already-validated player ID."""
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if not meetup:
            raise MeetupNotFoundError(str(meetup_date))

        if not meetup.is_signup_open():
            raise SignupClosedError("Cannot leave a meetup once teams have been assigned.")

        meetup.remove_player(player_id, self.default_capacity)

        self.meetup_repository.save(meetup)
        return meetup
