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

"""Call-up objects."""

import functools

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Final, Optional, Set

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pyball.bot import locale
from pyball.bot.errors import PlayerAlreadyCalledUpError, PlayerNotCalledUpError
from pyball.bot.logger import PYBALL_LOGGER
from pyball.settings import SUBSTITUTES_ID


class PlayerAction(Enum):
    """Represents the possible actions of a player."""

    JOIN = "join"
    LEAVE = "leave"

    def __str__(self) -> str:
        """Value of the enum member.

        :returns: The string object representation.

        """
        return self.value


CALL_UP_KEYBOARD: Final[InlineKeyboardMarkup] = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Me apunto!!! :)", callback_data=str(PlayerAction.JOIN))],
        [InlineKeyboardButton("Me borro :(", callback_data=str(PlayerAction.LEAVE))],
    ]
)


@dataclass
class ChatInfo:
    """Basic information needed from a chat.

    :ivar id: Chat identifier.
    :ivar msg: Call-up message identifier.

    """

    chat_id: str
    msg_id: Optional[str] = None


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

    def __compute_maximum(self) -> int:
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


class CallUp:
    """Necessary information involving a match call-up.

    :ivar __title: Summary of the call-up.
    :ivar __main_chat: Info about the main chat post.
    :ivar __subs_chat: Info about the substitutes chat post.
    :ivar __players: Object containing the list of players.

    """

    __slots__ = ["__title", "__main_chat", "__subs_chat", "__players", "__actions"]

    def __init__(self, title: str, main_chat_id: str, main_chat_msg: str) -> None:
        self.__title: str = title
        self.__main_chat: ChatInfo = ChatInfo(main_chat_id, main_chat_msg)
        self.__subs_chat: ChatInfo = ChatInfo(SUBSTITUTES_ID)
        self.__players: Players = Players()
        self.__actions: Dict[str, Callable] = {
            str(PlayerAction.JOIN): self.add_player,
            str(PlayerAction.LEAVE): self.del_player,
        }

    @property
    def title(self) -> str:
        """Get the title of the call-up.

        :returns: The title string.

        """
        return self.__title

    @property
    def players(self) -> Players:
        """Get the list of players called-up.

        :returns: The player object for this call-up.

        """
        return self.__players

    @property
    def subs_chat(self) -> ChatInfo:
        """Get the substitutes chat information.

        :returns: Substitutes chat id and message id.

        """
        return self.__subs_chat

    def act(self, action: PlayerAction, player: str) -> None:
        """Act depending on the player action.

        :param action: Action of joining or leaving the CallUp.
        :param player: Name of the player.

        """
        self.__actions[str(action)](player)

    def set_subs_message_id(self, message_id: Optional[str]) -> None:
        """Set the substitutes chat message identifier.

        :param message_id: The identifier of the substitutes search message or None.

        """
        self.__subs_chat.msg_id = message_id

    def remaining_players(self) -> int:
        """Return the number of remaining players for the call-up.

        :returns: Missing players.

        """
        return self.__players.remaining()

    def validate_message_id(self, request_message_id: str) -> bool:
        """Check if the requester message identifier matches with the main chat message id.

        :param request_message_id: The incomming message identifier.
        :returns: Whether the incomming message id is the same as the call-up message id.

        """
        return self.__main_chat.msg_id == request_message_id

    def is_searching(self) -> bool:
        """Check if the current call-up is searching for substitutes.

        :returns: Whether the call-up needs substitutes.

        """
        return self.__subs_chat.msg_id is not None

    def add_player(self, player_name: str) -> None:
        """Add player to the call-up.

        :param player_name: Name of the player who wants to join.

        """
        self.__players.join(player_name)

    def del_player(self, player_name: str) -> None:
        """Remove a player from the call-up.

        :param player_name: Name of the player who wants to leave.

        """
        self.__players.leave(player_name)

    def __str__(self) -> str:
        """Text that shows the call-up title and the players called-up.

        :returns: The call-up message.

        """
        return f"Lista de jugadores para la convocatoria *{self.title}*\n{str(self.players)}"
