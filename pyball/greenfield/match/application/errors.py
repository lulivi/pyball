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

"""Common match use case errors."""

import datetime
import uuid


class MatchIdNotFound(Exception):
    """The match was not found."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"There is no match with the id `{id}` does not exist"
        super().__init__(self.message)


class MatchDateNotFound(Exception):
    """The match was not found."""

    def __init__(self, date_time: datetime.datetime) -> None:
        self.date_time = date_time
        self.message = f"There is no match with the date `{date_time}` does not exist"
        super().__init__(self.message)


class PlayerIsAlreadyInMatch(Exception):
    """The player is already in the match."""

    def __init__(self, match_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.match_id = match_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is already in the match `{match_id}`"
        super().__init__(self.message)
