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


class PyBallDbError(Exception):
    """Base error for PyBall database transactions."""


class PlayerNotUpdatedError(PyBallDbError):
    """The player was not updated."""


class PlayerAlreadyExistentError(PyBallDbError):
    """The player is already in the database."""

    def __init__(self, name: str, id: int) -> None:
        self.name = name
        self.id = id
        self.message = f"Player `{self.name}` already in the database (with id: `{self.id}`)"
        super().__init__(self.message)


class StatisticForPlayerInMatchAlreadyExistent(PyBallDbError):
    """The statistic for that player in that match is already in the database."""

    def __init__(self, date: datetime.datetime, player: str) -> None:
        self.date = date
        self.player = player
        self.message = f"Player `{self.player}` already has a statistic in `{self.date}` match"
        super().__init__(self.message)


class InconsistencyError(PyBallDbError):
    """There is an inconsistency in the database."""


class ScoreInconsistencyError(InconsistencyError):
    """There is an inconsitency error related to the goals or assis."""


class MatchesCountInconsistencyError(InconsistencyError):
    """There is an inconsitency error related to the number of wins, losses and ties."""
