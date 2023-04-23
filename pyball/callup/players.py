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
import logging

from enum import Enum, auto
from typing import List, Union

from pyball import db
from pyball.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.db import wrapper
from pyball.db.utils import find_player

logger = logging.getLogger(__name__)


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

    def __init__(self) -> None:
        """Initialize the object."""
        self.__players: List[db.wrapper.Player] = []
        self.__maximum: int
        self.__compute_maximum()
        logger.debug("Created the Players object")

    @property
    def players(self) -> List[db.wrapper.Player]:
        """Obtain the list of players.

        :returns: All the called-up players.

        """
        return self.__players

    def join(self, player: Union[str, int]) -> None:
        """Join the call-up.

        :param player: The player identifier or name.
        :raises CallUpPlayerDoesNotExistError: If the player is not found in the database.
        :raises CallUpPlayerAlreadyCalledUpError: If the player is already in the call-up list.

        """
        logger.debug(f"Adding player `{player}`")

        try:
            player_object: wrapper.Player = find_player(player)
        except db.model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
            logger.error(f"Adding player `{player}`: Player not found in the database")
            raise CallUpPlayerDoesNotExistError(player) from error
        except db.errors.DbMultiplePlayersFoundError as error:
            logger.error(f"Adding player `{player}`: Multiple players found in the database")
            raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error

        if player_object in self.__players:
            logger.error(f"Adding player `{player}`: Already in `{player_object.name}`")
            raise CallUpPlayerAlreadyCalledUpError(
                f"El jugador `{player_object}` ya está apuntado a esta convocatoria"
            )

        logger.debug(f"Adding player `{player}`: Added `{player_object.name}`")
        self.__players.append(player_object)
        self.__compute_maximum()

    def leave(self, player: Union[str, int]) -> None:
        """Leave the call-up.

        :param player: The player identifier or name.
        :raises CallUpPlayerDoesNotExistError: If the player is not found in the database.
        :raises CallUpPlayerNotCalledUpError: If the player is hasn't been called-up.

        """
        logger.debug(f"Removing player `{player}`")

        try:
            player_object: wrapper.Player = find_player(player)
        except db.model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
            logger.error(f"Removing player `{player}`: Player not found in the database")
            raise CallUpPlayerDoesNotExistError(player) from error
        except db.errors.DbMultiplePlayersFoundError as error:
            logger.error(f"Removing player `{player}`: Multiple players found in the database")
            raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error

        try:
            self.__players.remove(player_object)
            logger.debug(f"Removing player `{player}`: Removed `{player_object.name}`")
        except ValueError as error:
            logger.debug(f"Removing player `{player}`: Not in `{player_object}`")
            raise CallUpPlayerNotCalledUpError(
                f"El jugador `{player_object}` no está apuntado a esta convocatoria"
            ) from error

        self.__compute_maximum()

    def __compute_maximum(self) -> None:
        """Guess the maximum number of player based on the current one.

        :param n_signed__players: Number of signed players.
        :returns: The maximum number of players to search for.

        """
        self.__maximum = min(filter(lambda x: len(self) <= x, (10, 12, 15, 20, 25)), default=100)

    def remaining(self) -> int:
        """Get the remaining number of player necessary for the call-up.

        :returns: The difference between the maximum and the current number of players.

        """
        return self.__maximum - len(self)

    def __len__(self) -> int:
        """Obtain the number of players signed up for the call-up.

        :returns: The number of players signed up.

        """
        return len(self.__players)

    def __str__(self) -> str:
        # Since we don't want UTF-8 characters to mess up the sorting, we use the
        # :func:`functools.cmp_to_key` function with the chosen locale.
        sorted_players = sorted(
            [p.name for p in self.__players], key=functools.cmp_to_key(locale.strcoll)
        )
        sorted_players.extend(["?????"] * (self.__maximum - len(self.__players)))
        return "\n".join(
            [f"{index + 1:02} - `{player}`" for index, player in enumerate(sorted_players)]
        )
