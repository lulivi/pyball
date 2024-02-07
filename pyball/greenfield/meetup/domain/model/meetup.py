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

"""Meetup domain model object."""

import datetime
import uuid

from ast import Tuple
from typing import List, Optional

Team = List[uuid.UUID]


class Meetup:
    def __init__(self, id: uuid.UUID, date_time: datetime.datetime, location: str):
        if not isinstance(id, uuid.UUID):
            raise AttributeError("The uuid is not a UUID object")
        self._id: uuid.UUID = id
        self._date_time: datetime.datetime = date_time
        self._location: str = location
        self._players: List[uuid.UUID] = []
        self._teams: Optional[Team] = None

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def date_time(self) -> datetime.datetime:
        return self._date_time

    @property
    def location(self) -> str:
        return self._location

    @property
    def players(self) -> List[uuid.UUID]:
        return self._players

    @property
    def teams(self) -> Optional[List[Team]]:
        return self._teams

    def add_player(self, id: uuid.UUID) -> None:
        self._players.append(id)

        if self.calculate_team_count(len(self._players)) > 0:
            self.create_teams()

    @staticmethod
    def calculate_team_count(player_count: int, possible_team_sizes=(5, 6)) -> int:
        for team_size in possible_team_sizes:
            if player_count % team_size == 0 and player_count > team_size:
                return player_count // team_size

        return 0

    def create_teams(self) -> None:
        team_player_count = len(self.players) // 2
        # TODO: This only contemplates 2 teams, what happens with 3 teams?
        self._teams = [
            self._players[:team_player_count],
            self._players[team_player_count:],
        ]

    def __contains__(self, player_id: uuid.UUID) -> bool:
        return player_id in self._players
