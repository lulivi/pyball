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

from dataclasses import dataclass
from typing import List, Optional, Tuple

from pyball.meetup.domain.errors import InvalidPlayerCountError
from pyball.utils.aggregate import Aggregate, Event

Team = List[uuid.UUID]


class Meetup(Aggregate):
    def __init__(
        self,
        id: uuid.UUID,
        date_time: datetime.datetime,
        location: str,
        possible_team_sizes: Tuple[int, ...] = (5, 6),
        players: Optional[List[uuid.UUID]] = None,
        teams: Optional[List[Team]] = None,
    ):
        if not isinstance(id, uuid.UUID):
            raise AttributeError("The uuid is not a UUID object")
        self._id: uuid.UUID = id
        self._date_time: datetime.datetime = date_time
        self._location: str = location
        self._possible_team_sizes = possible_team_sizes
        self._players: List[uuid.UUID] = players or []
        self._teams: List[Team] = teams or []

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
    def possible_team_sizes(self) -> tuple:
        return self._possible_team_sizes

    @property
    def players(self) -> List[uuid.UUID]:
        return self._players

    @property
    def team_count(self) -> int:
        # TODO: Refactor
        player_count = len(self._players)
        for team_size in self._possible_team_sizes:
            if player_count % team_size == 0 and player_count > team_size:
                return player_count // team_size

        return 0

    @property
    def teams(self) -> List[Team]:
        return self._teams

    def add_player(self, id: uuid.UUID) -> None:
        self._players.append(id)
        self.trigger_event(self.PlayerWasAdded(self._id, id))

    def remove_player(self, id: uuid.UUID) -> None:
        self._players.remove(id)
        self.trigger_event(self.PlayerWasRemoved(self._id, id))

    def create_teams(self) -> None:
        if self.team_count == 0:
            raise InvalidPlayerCountError()

        team_player_count = len(self.players) // self.team_count
        self._teams = []

        for player_chunk_index in range(0, len(self._players), team_player_count):
            self._teams.append(
                self._players[player_chunk_index : player_chunk_index + team_player_count]
            )

        self.trigger_event(self.TeamsWereCreated(self._id, self._teams))

    def __contains__(self, player_id: uuid.UUID) -> bool:
        return player_id in self._players

    @dataclass
    class PlayerWasAdded(Event):
        meetup_id: uuid.UUID
        player_id: uuid.UUID

    @dataclass
    class PlayerWasRemoved(Event):
        meetup_id: uuid.UUID
        player_id: uuid.UUID

    @dataclass
    class TeamsWereCreated(Event):
        meetup_id: uuid.UUID
        teams: List[Team]
