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

"""Create a new meetup use case."""

import datetime
import uuid

from pyball.greenfield.meetup.domain.errors import (
    MeetupAlreadyExistentError,
    MeetupDateAlreadyUsedError,
)
from pyball.greenfield.meetup.domain.meetups import Meetups
from pyball.greenfield.meetup.domain.model.meetup import Meetup


class CreateMeetup:
    def __init__(self, meetup_repository: Meetups) -> None:
        self._meetups = meetup_repository

    def create(self, id: uuid.UUID, date_time: datetime.datetime, location: str) -> None:
        if self._meetups.get(id=id) is not None:
            raise MeetupAlreadyExistentError(id=id)

        if self._meetups.get_by_date(date_time=date_time) is not None:
            raise MeetupDateAlreadyUsedError(date_time=date_time)

        meetup = Meetup(id=id, date_time=date_time, location=location)
        self._meetups.save(meetup)
