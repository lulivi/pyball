# Copyright (c) 2023 Luis Liñán
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

"""Add a player to a meetup use case."""

import uuid

from pyball.greenfield.meetup.application.errors import MeetupIdNotFound, PlayerIsAlreadyInMeetup
from pyball.greenfield.meetup.domain.meetups import Meetups


class AddPlayerToMeetup:
    def __init__(self, meetup_repository: Meetups) -> None:
        self._meetup = meetup_repository

    def add(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        meetup = self._meetup.get(id=meetup_id)

        if meetup is None:
            raise MeetupIdNotFound(id=meetup_id)

        if player_id in meetup:
            raise PlayerIsAlreadyInMeetup(meetup_id=meetup_id, player_id=player_id)

        meetup.add_player(id=player_id)
        self._meetup.save(meetup=meetup)
