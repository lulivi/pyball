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

from typing import Optional

from pyball.meetup.application.errors import (
    MeetupIdNotFound,
    PlayerIsAlreadyInMeetup,
    PlayerNotFound,
)
from pyball.meetup.domain.meetups import Meetups
from pyball.meetup.domain.model.meetup import Meetup
from pyball.meetup.domain.player_checker import IPlayerChecker


class AddPlayerToMeetup:
    def __init__(self, meetup_repository: Meetups, player_checker: IPlayerChecker) -> None:
        self._meetup = meetup_repository
        self._player_checker = player_checker

    def add(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        meetup: Optional[Meetup] = self._meetup.get(id=meetup_id)

        if meetup is None:
            raise MeetupIdNotFound(id=meetup_id)

        if player_id in meetup:
            raise PlayerIsAlreadyInMeetup(meetup_id=meetup_id, player_id=player_id)

        if not self._player_checker.check_player_exists(player_id=player_id):
            raise PlayerNotFound(id=player_id)

        meetup.add_player(id=player_id)
        self._meetup.save(meetup=meetup)
