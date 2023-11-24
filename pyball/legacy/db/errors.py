# Copyright (c) 2022 Luis Liñán
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

"""Errors related to the database."""

import datetime

from typing import List, Optional


class PyBallDbError(Exception):
    """Base error for PyBall database transactions."""


class DbPlayerNotFoundError(PyBallDbError):
    """The player was not found."""

    def __init__(self, wild_card: str) -> None:
        self.wild_card = wild_card
        self.message = f"The search of `{self.wild_card}` gave no results"
        super().__init__(self.message)


class DbPlayerStatisticsNotFoundError(PyBallDbError):
    """The player statistics were not found."""

    def __init__(self, wild_card: str) -> None:
        self.wild_card = wild_card
        self.message = (
            f"The search of `{self.wild_card}` gave no results for the player statistics"
        )
        super().__init__(self.message)


class DbMatchStatisticsNotFoundError(PyBallDbError):
    """The match date didn't give any results."""

    def __init__(self, date: datetime.datetime) -> None:
        self.date = date
        self.message = f"Could not find any match statistic for the date `{self.date}`"
        super().__init__(self.message)


class DbPlayerNotUpdatedError(PyBallDbError):
    """The player was not updated."""


class DbPlayerAlreadyExistentError(PyBallDbError):
    """The player is already in the database."""

    def __init__(self, name: str, identifier: Optional[int]) -> None:
        self.name = name
        self.identifier = identifier
        self.message = (
            f"Player `{self.name}` already in the database (with id: `{self.identifier}`)"
        )
        super().__init__(self.message)


class DbPlayerStatsAlreadyExistentError(PyBallDbError):
    """The player stats table already contains a row for the player."""

    def __init__(self, name: str, table: str) -> None:
        self.name = name
        self.table = table
        self.message = f"Player `{self.name}` already in the stats table `{self.table}`"
        super().__init__(self.message)


class DbMultiplePlayersFoundError(PyBallDbError):
    """When the wildcard search of a player is general enough to find more than one."""

    def __init__(self, player_names: List[str], wild_card: str) -> None:
        self.players = player_names
        self.wild_card = wild_card
        self.message = (
            f"Multiple players found when searching for the wild-card `{self.wild_card}`:"
            f" `{'`, `'.join(self.players)}`"
        )
        super().__init__(self.message)


class DbStatisticForPlayerInMatchAlreadyExistent(PyBallDbError):
    """The statistic for that player in that match is already in the database."""

    def __init__(self, date: datetime.datetime, player: str) -> None:
        self.date = date
        self.player = player
        self.message = f"Player `{self.player}` already has a statistic in `{self.date}` match"
        super().__init__(self.message)


class DbInconsistencyError(PyBallDbError):
    """There is an inconsistency in the database."""


class DbScoreInconsistencyError(DbInconsistencyError):
    """There is an inconsitency error related to the goals or assis."""


class DbMatchesCountInconsistencyError(DbInconsistencyError):
    """There is an inconsitency error related to the number of wins, losses and ties."""


class DbUnknownResultError(PyBallDbError):
    """The result provided is not correct."""

    def __init__(self, result: str) -> None:
        self.result = result
        self.message = (
            f"The result provided (`{self.result}`) is not one of `wins`, `losses` and `ties`"
        )
        super().__init__(self.message)


class DbNoBackUpError(PyBallDbError):
    """There is no backup database."""
