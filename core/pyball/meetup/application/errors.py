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

"""Common meetup use case errors."""

import datetime
import uuid


class MeetupIdNotFound(Exception):
    """The meetup was not found."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"There is no meetup with the id `{id}`"
        super().__init__(self.message)


class MeetupDateNotFound(Exception):
    """The meetup was not found."""

    def __init__(self, date_time: datetime.datetime) -> None:
        self.date_time = date_time
        self.message = f"There is no meetup with the date `{date_time}`"
        super().__init__(self.message)


class PlayerIsAlreadyInMeetup(Exception):
    """The player is already in the meetup."""

    def __init__(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.meetup_id = meetup_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is already in the meetup `{meetup_id}`"
        super().__init__(self.message)

class PlayerIsNotInMeetup(Exception):
    """The player is not in the meetup."""

    def __init__(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.meetup_id = meetup_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is not in the meetup `{meetup_id}`"
        super().__init__(self.message)


class PlayerNotFound(Exception):
    """The player was not found meetup."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player `{id}` could not be found in the players repository"
        super().__init__(self.message)
