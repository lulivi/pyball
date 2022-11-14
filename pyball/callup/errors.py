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

"""Call-up related errors."""
from typing import List


class PyBallCallUpError(Exception):
    """Base error for PyBall bot."""


class CallUpPlayerDoesNotExistError(PyBallCallUpError):
    """The player is not found in the database."""


class CallUpPlayerAlreadyCalledUpError(PyBallCallUpError):
    """The player is already in the call-up."""


class CallUpPlayerNotCalledUpError(PyBallCallUpError):
    """The player hasn't been called-up."""


class CallUpMatchWrongPlayersNumberError(PyBallCallUpError):
    """The number of player for the match is wrong."""

    def __init__(self, current_players: int) -> None:
        self.current_players = current_players
        self.message = (
            f"The number of players (`{current_players}`) cannot evenly create 2 or 3 teams"
        )
        super().__init__(self.message)


class CallUpMatchNotYetCreatedError(PyBallCallUpError):
    """The match hasn't been created yet."""


class CallUpStatisticOfNonPlayers(PyBallCallUpError):
    """There are statistics of players that are not in any of the teams."""

    def __init__(self, non_players: List[str]) -> None:
        self.non_players = non_players
        self.message = f"Players `{self.non_players}` are not in any of the teams"
        super().__init__(self.message)
