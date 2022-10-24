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

"""Players object."""

import functools
import locale

from enum import Enum, auto
from typing import Set

from pyball.callup.errors import PlayerAlreadyCalledUpError, PlayerNotCalledUpError
from pyball.logger import PYBALL_LOGGER


class PlayerAction(Enum):
    """Represents the possible actions of a player."""

    JOIN = auto()
    LEAVE = auto()


class Players:
    """Simple class to manage the called players for a game.

    :ivar __players: The list of players.
    :ivar _maximum: The max number to search player for.

    """

    __slots__ = ["__players", "__maximum"]

    def __init__(self):
        """Initialize the object."""
        self.__players: Set[str] = set()
        self.__maximum: int
        self.__compute_maximum()

    def remaining(self) -> int:
        """Get the remaining number of player necessary for the call-up.

        :returns: The difference between the maximum and the current number of players.

        """
        return self.__maximum - len(self)

    def join(self, player_name: str) -> None:
        """Join the call-up.

        :param player_name: The player that wants to join the call-up.
        :raises PlayerAlreadyCalledUpError: If the player is already in the call-up list.

        """
        PYBALL_LOGGER.debug(f"Trying to add the player `{player_name}`")

        if player_name in self.__players:
            PYBALL_LOGGER.debug(f"The player is already in the list")
            raise PlayerAlreadyCalledUpError(
                f"El jugador {player_name} ya está apuntado a esta convocatoria"
            )

        self.__players.add(player_name)
        self.__compute_maximum()

    def leave(self, player: str) -> None:
        """Leave the call-up.

        :param player_name: The player that wants to leave the call-up.
        :raises PlayerNotCalledUpError: If the player is hasn't been called-up.

        """
        PYBALL_LOGGER.debug(f"Trying to remove the player `{player}`")

        try:
            self.__players.remove(player)
        except KeyError:
            PYBALL_LOGGER.debug(f"The player is not in the list")
            raise PlayerNotCalledUpError(
                f"El jugador {player} no está apuntado a esta convocatoria"
            )
        self.__compute_maximum()

    def __compute_maximum(self) -> None:
        """Guess the maximum number of player based on the current one.

        :param n_signed__players: Number of signed players.
        :returns: The maximum number of players to search for.

        """
        self.__maximum = min(filter(lambda x: len(self) <= x, (10, 12, 15, 20, 25)), default=100)

    def __len__(self) -> int:
        """Obtain the number of players signed up for the call-up.

        :returns: The number of players signed up.

        """
        return len(self.__players)

    def __str__(self) -> str:
        """List of players signed up for the call-up.

        Since we don't want UTF-8 characters to mess up the sorting, we use the
        :func:`functools.cmp_to_key` function with the chosen locale.

        :returns: The string representation of the players.

        """
        sorted_players = sorted(self.__players, key=functools.cmp_to_key(locale.strcoll))
        sorted_players.extend(["?????"] * (self.__maximum - len(self.__players)))
        return "\n".join(
            [f"{index + 1:0>2} - {player}" for index, player in enumerate(sorted_players)]
        )
