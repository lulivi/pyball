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

"""Match domain model object."""

import datetime
import uuid

from typing import List


class Match:
    def __init__(self, id: uuid.UUID, date: datetime.datetime, location: str):
        if not isinstance(id, uuid.UUID):
            raise AttributeError("The uuid is not a UUID object")
        self._id: uuid.UUID = id
        self._date: datetime.datetime = date
        self._location: str = location
        self._players: List[uuid.UUID] = []

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def location(self) -> str:
        return self._location

    @property
    def players(self) -> List[uuid.UUID]:
        return self._players

    def add_player(self, id: uuid.UUID) -> None:
        self._players.append(id)

    def __contains__(self, player: uuid.UUID) -> bool:
        return player in self._players
