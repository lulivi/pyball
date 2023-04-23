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

"""Call-up object."""

import datetime
import logging

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Union

from pyball.__version__ import __version__
from pyball.callup.errors import CallUpMatchNotYetCreatedError
from pyball.callup.match import Match, PlayersStatInput
from pyball.callup.players import PlayerAction, Players
from pyball.settings import SUBSTITUTES_ID

logger = logging.getLogger(__name__)


@dataclass
class ChatInfo:
    """Basic information needed from a chat.

    :ivar id: Chat identifier.
    :ivar msg: Call-up message identifier.

    """

    chat_id: int
    message_id: Optional[int] = None

    def as_dict(self) -> Dict[str, int]:
        """Return the instance variables as a dictionary."""
        return vars(self)


class CallUp:
    """Necessary information involving a match call-up.

    :ivar __date: Call-up date.
    :ivar __title: Summary of the call-up.
    :ivar __main_chat: Info about the main chat post.
    :ivar __subs_chat: Info about the substitutes chat post.
    :ivar __players: Object containing the list of players.
    :cvar __actions: Dictionary containing the two actions for a player to do in
        a call-up.

    """

    __slots__ = [
        "__date",
        "__title",
        "__main_chat",
        "__subs_chat",
        "__players",
        "__actions",
        "__match",
    ]
    __actions: Dict[str, Callable]

    def __init__(self, date: datetime.datetime, main_chat_id: int, main_chat_msg: int) -> None:
        self.__date: datetime.datetime = date
        self.__title: str = datetime.datetime.strftime(date, "%A %Y/%m/%d %H:%M")
        self.__main_chat: ChatInfo = ChatInfo(main_chat_id, main_chat_msg)
        self.__subs_chat: ChatInfo = ChatInfo(SUBSTITUTES_ID)
        self.__players: Players = Players()
        self.__actions = {
            PlayerAction.JOIN.name: self.add_player,
            PlayerAction.LEAVE.name: self.del_player,
        }
        self.__match: Optional[Match] = None
        logger.debug(f"Creating a new call-up: {self.__title}")

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
    def match(self) -> Match:
        """Obtain the Match object.

        If the teams are not created, this call will create them.

        :returns: The match.

        """
        if not self.__match:
            raise CallUpMatchNotYetCreatedError(
                "The match hasn't been created yet, so no results can be set"
            )

        return self.__match

    @property
    def main_chat(self) -> ChatInfo:
        """Get the main chat information.

        :returns: Main chat id and message id.

        """
        return self.__main_chat

    @property
    def subs_chat(self) -> ChatInfo:
        """Get the substitutes chat information.

        :returns: Substitutes chat id and message id.

        """
        return self.__subs_chat

    def act(self, action: str, player: Union[str, int]) -> None:
        """Act depending on the player action.

        :param action: Action of joining or leaving the CallUp.
        :param player: Name of the player.

        """
        self.__actions[action](player)

    def set_subs_message_id(self, message_id: Optional[int]) -> None:
        """Set the substitutes chat message identifier.

        :param message_id: The identifier of the substitutes search message or None.

        """
        self.__subs_chat.message_id = message_id

    def reset_subs_message_id(self) -> None:
        """Reset the substitutes chat message identifier."""
        self.__subs_chat.message_id = None

    def remaining_players(self) -> int:
        """Return the number of remaining players for the call-up.

        :returns: Missing players.

        """
        return self.__players.remaining()

    def validate_message_id(self, request_message_id: int) -> bool:
        """Check if the requester message identifier matches with the main chat message id.

        :param request_message_id: The incomming message identifier.
        :returns: Whether the incomming message id is the same as the call-up message id.

        """
        return self.__main_chat.message_id == request_message_id

    def is_searching(self) -> bool:
        """Check if the current call-up is searching for substitutes.

        :returns: Whether the call-up needs substitutes.

        """
        return self.__subs_chat.message_id is not None

    def add_player(self, player: Union[str, int]) -> None:
        """Add player to the call-up.

        :param player_name: Name of the player who wants to join.

        """
        self.__players.join(player)
        self.__match = None

    def del_player(self, player: Union[str, int]) -> None:
        """Remove a player from the call-up.

        :param player_name: Name of the player who wants to leave.

        """
        self.__players.leave(player)
        self.__match = None

    def create_match(self) -> None:
        """Create a new match."""
        self.__match = Match(self.__players)

    def set_results(self, results: PlayersStatInput) -> None:
        """Introduce the results of the match.

        :param results: The results object.

        """
        if self.__match is None:
            raise CallUpMatchNotYetCreatedError(
                "The match hasn't been created yet, so no results can be set"
            )

        self.__match.set_results(results, self.__date)

    def __str__(self) -> str:
        output = f"Convocatoria: *{self.__title}*\n\n{str(self.__players)}"

        if self.__match is not None:
            output = f"{output}\n{str(self.__match)}"

        output = f"{output}\n\nVersion: `{__version__}`"

        return output
