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

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from pyball.callup.players import PlayerAction, Players
from pyball.settings import SUBSTITUTES_ID


@dataclass
class ChatInfo:
    """Basic information needed from a chat.

    :ivar id: Chat identifier.
    :ivar msg: Call-up message identifier.

    """

    chat_id: str
    msg_id: Optional[str] = None


class CallUp:
    """Necessary information involving a match call-up.

    :ivar __title: Summary of the call-up.
    :ivar __main_chat: Info about the main chat post.
    :ivar __subs_chat: Info about the substitutes chat post.
    :ivar __players: Object containing the list of players.

    """

    __slots__ = ["__title", "__main_chat", "__subs_chat", "__players", "__actions"]
    __actions: Dict[str, Callable]

    def __init__(self, title: str, main_chat_id: str, main_chat_msg: str) -> None:
        self.__title: str = title
        self.__main_chat: ChatInfo = ChatInfo(main_chat_id, main_chat_msg)
        self.__subs_chat: ChatInfo = ChatInfo(SUBSTITUTES_ID)
        self.__players: Players = Players()
        self.__actions = {
            PlayerAction.JOIN.name: self.add_player,
            PlayerAction.LEAVE.name: self.del_player,
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

    def act(self, action: str, player: str) -> None:
        """Act depending on the player action.

        :param action: Action of joining or leaving the CallUp.
        :param player: Name of the player.

        """
        self.__actions[action](player)

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
