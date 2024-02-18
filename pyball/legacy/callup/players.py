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
from typing import List, Optional, Union

import yaml

from pyball.legacy import db
from pyball.legacy.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)

logger = logging.getLogger(__name__)


class Players:
    """Simple class to manage the called players for a game.

    :ivar _players: The list of players.
    :ivar _maximum: The max number to search player for.

    """

    __slots__ = ["_players", "_fixed_player_number"]

    def __init__(
        self,
        maximum: Optional[int] = None,
        players: Optional[List[db.wrapper.Player]] = None,
    ) -> None:
        """Initialize the object."""
        self._players: List[db.wrapper.Player] = players or []
        self._fixed_player_number: Optional[int] = maximum
        logger.debug("Created the Players object")

    @property
    def maximum(self) -> int:
        """Get the fixed maximum number of players or calculate a dynamic one.

        When the `_maximum` attribute is None, the maximum number of players will be selected
        dynamically by the :func:`_compute_maximum` function. If it is defined, the fixed value
        will be returned.

        :returns: The maximum number of players.

        """
        if self._fixed_player_number is None:
            return self._compute_maximum()

        return self._fixed_player_number

    def set_maximum(self, new_maximum: Optional[int]) -> None:
        """Set the maximum value to a new maximum, or to an automatic one.

        :param new_maximum: A number to represent the new maximum or `None` to calculate depending
            on the current players.

        """
        self._fixed_player_number = new_maximum

    def _compute_maximum(self) -> int:
        """Guess the maximum number of player based on the current one.

        :param n_signed_players: Number of signed players.
        :returns: The maximum number of players to search for.

        """
        return min(filter(lambda x: len(self) <= x, (10, 12, 14, 15, 22)), default=100)

    @property
    def players(self) -> List[db.wrapper.Player]:
        """Obtain the list of players.

        :returns: All the called-up players.

        """
        return self._players

    def join(self, player: Union[str, int]) -> None:
        """Join the call-up.

        :param player: The player identifier or name.
        :raises CallUpPlayerDoesNotExistError: If the player is not found in the database.
        :raises CallUpPlayerAlreadyCalledUpError: If the player is already in the call-up list.

        """
        logger.debug(f"Adding player `{player}`")
        player_object: db.wrapper.Player = find_player(player)

        if player_object in self._players:
            logger.error(f"Adding player `{player}`: Already in `{player_object.name}`")
            raise CallUpPlayerAlreadyCalledUpError(
                f"El jugador `{player_object}` ya está apuntado a esta convocatoria"
            )

        if self.are_ready():
            self._fixed_player_number = None

        logger.debug(f"Adding player `{player}`: Added `{player_object.name}`")
        self._players.append(player_object)

    def leave(self, player: Union[str, int]) -> None:
        """Leave the call-up.

        :param player: The player identifier or name.
        :raises CallUpPlayerDoesNotExistError: If the player is not found in the database.
        :raises CallUpPlayerNotCalledUpError: If the player is hasn't been called-up.

        """
        logger.debug(f"Removing player `{player}`")
        player_object: db.wrapper.Player = find_player(player)

        try:
            self._players.remove(player_object)
            logger.debug(f"Removing player `{player}`: Removed `{player_object.name}`")
        except ValueError as error:
            logger.debug(f"Removing player `{player}`: Not in `{player_object}`")
            raise CallUpPlayerNotCalledUpError(
                f"El jugador `{player_object}` no está apuntado a esta convocatoria"
            ) from error

    def remaining(self) -> int:
        """Get the remaining number of player necessary for the call-up.

        :returns: The difference between the maximum and the current number of players.

        """
        return self.maximum - len(self)

    def are_ready(self) -> bool:
        """Find if the players are ready to play.

        :returns: If there are no remaining players to search and the match can be created.

        """
        return self.remaining() == 0

    def __len__(self) -> int:
        """Obtain the number of players signed up for the call-up.

        :returns: The number of players signed up.

        """
        return len(self._players)

    def __str__(self) -> str:
        return self.to_yaml()

    def __repr__(self) -> str:
        # Since we don't want UTF-8 characters to mess up the sorting, we use the
        # :func:`functools.cmp_to_key` function with the chosen locale.
        sorted_players = sorted(
            [p.name for p in self._players], key=functools.cmp_to_key(locale.strcoll)
        )
        sorted_players.extend(["?????"] * (self.maximum - len(self._players)))
        player_list = ",".join(sorted_players)
        return f"Players({player_list})"

    def to_yaml(self) -> str:
        """Obtain the YAML representation of the players.

        :returns: The YAML string.

        """
        return yaml.dump(
            {
                "jugadores": sorted(
                    [f"`{p.name}`" for p in self._players],
                    key=functools.cmp_to_key(locale.strcoll),
                )
                + ["`?????`"] * (self.maximum - len(self._players))
            },
            allow_unicode=True,
            indent=4,
            sort_keys=False,
        )

    @staticmethod
    def from_list(players_info: List[str]) -> "Players":
        """Recreate a Player object from a list of player names.

        :param players_info: The list with all the players.

        """
        return Players(
            maximum=len(players_info) if "?????" in players_info else None,
            players=[
                find_player(player_name) for player_name in players_info if player_name != "?????"
            ],
        )


def find_player(player: Union[str, int]) -> db.wrapper.Player:
    """Wrap db.utils.find_player and raise proper errors.

    :param player: The name or id of the player to get.
    :returns: The player object.

    """
    try:
        return db.utils.find_player(player, all_seasons=True)
    except db.errors.DbPlayerNotFoundError as error:
        logger.error(f"Player `{player}` not found in the database")
        raise CallUpPlayerDoesNotExistError(player) from error
    except db.errors.DbMultiplePlayersFoundError as error:
        logger.error(f"Multiple players found in the database for the search `{player}`")
        raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error
