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

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Union

import yaml

from pyball import __version__
from pyball.callup.errors import (
    CallUpMatchAlreadyFinishedError,
    CallUpMatchNotYetCreatedError,
    CallUpWrongFormatError,
)
from pyball.callup.match import Match, PlayersStatInput
from pyball.callup.players import PlayerAction, Players
from pyball.settings import DEFAULT_MATCH_LOCATION, SUBSTITUTES_ID

logger = logging.getLogger(__name__)


@dataclass
class ChatInfo:
    """Basic information needed from a chat.

    :ivar id: Chat identifier.
    :ivar msg: Call-up message identifier.

    """

    chat_id: int
    message_id: Optional[int] = None


class CallUp:
    """Necessary information involving a match call-up.

    :ivar _date: Call-up date.
    :ivar _location: Call-up location.
    :ivar _main_chat: Info about the main chat post.
    :ivar _subs_chat: Info about the substitutes chat post.
    :ivar _players: Object containing the list of players.
    :cvar _actions: Dictionary containing the two actions for a player to do in
        a call-up.
    :ivar _match: Object containing the teams of the call-up.

    """

    __slots__ = [
        "_date",
        "_location",
        "_main_chat",
        "_subs_chat",
        "_players",
        "_actions",
        "_match",
    ]
    _actions: Dict[str, Callable]

    def __init__(
        self,
        date: datetime.datetime,
        main_chat_id: int,
        main_chat_msg: int,
        subs_chat_msg: Optional[int] = None,
        location: Optional[str] = None,
        fixed_player_number: Optional[int] = None,
        players: Optional[Players] = None,
        match: Optional[Match] = None,
    ) -> None:
        self._date: datetime.datetime = date
        self._location: str = location or DEFAULT_MATCH_LOCATION
        self._main_chat: ChatInfo = ChatInfo(main_chat_id, main_chat_msg)
        self._subs_chat: ChatInfo = ChatInfo(SUBSTITUTES_ID, subs_chat_msg)
        self._players: Players = players or Players(maximum=fixed_player_number)
        self._actions = {
            PlayerAction.JOIN.name: self.add_player,
            PlayerAction.LEAVE.name: self.del_player,
        }
        self._match: Optional[Match] = match
        logger.debug(f"Creating a new call-up: {self.title}")

    @property
    def date(self) -> str:
        """Obtain the date string."""
        return self._date.strftime("%A %d/%b/%Y")

    @property
    def time(self) -> str:
        """Obtain the time string."""
        return self._date.strftime("%H:%M")

    @property
    def location(self) -> str:
        """Obtain the location."""
        return self._location

    @property
    def title(self) -> str:
        """Get the title of the call-up.

        :returns: The title string.

        """
        return (
            f"*Convocatoria*\nFecha *{self.date}*\nHora: *{self.time}*\nLugar: *{self.location}*"
        )

    @property
    def players(self) -> Players:
        """Get the list of players called-up.

        :returns: The player object for this call-up.

        """
        return self._players

    @property
    def match(self) -> Match:
        """Obtain the Match object.

        If the teams are not created, this call will create them.

        :returns: The match.

        """
        if not self._match:
            raise CallUpMatchNotYetCreatedError(
                "The match hasn't been created yet, so no results can be set"
            )

        return self._match

    @property
    def main_chat(self) -> ChatInfo:
        """Get the main chat information.

        :returns: Main chat id and message id.

        """
        return self._main_chat

    @property
    def subs_chat(self) -> ChatInfo:
        """Get the substitutes chat information.

        :returns: Substitutes chat id and message id.

        """
        return self._subs_chat

    def act(self, action: str, player: Union[str, int]) -> None:
        """Act depending on the player action.

        :param action: Action of joining or leaving the CallUp.
        :param player: Name of the player.

        """
        self._actions[action](player)

    def set_subs_message_id(self, message_id: Optional[int]) -> None:
        """Set the substitutes chat message identifier.

        :param message_id: The identifier of the substitutes search message or None.

        """
        self._subs_chat.message_id = message_id

    def reset_subs_message_id(self) -> None:
        """Reset the substitutes chat message identifier."""
        self._subs_chat.message_id = None

    def remaining_players(self) -> int:
        """Return the number of remaining players for the call-up.

        :returns: Missing players.

        """
        return self._players.remaining()

    def validate_message_id(self, request_message_id: int) -> bool:
        """Check if the requester message identifier matches with the main chat message id.

        :param request_message_id: The incomming message identifier.
        :returns: Whether the incomming message id is the same as the call-up message id.

        """
        return self._main_chat.message_id == request_message_id

    def is_searching(self) -> bool:
        """Check if the current call-up is searching for substitutes.

        :returns: Whether the call-up needs substitutes.

        """
        return self._subs_chat.message_id is not None

    def add_player(self, player: Union[str, int]) -> None:
        """Add player to the call-up.

        :param player_name: Name of the player who wants to join.

        """
        self._players.join(player)
        self._match = None

        if self._players.are_ready():
            self.create_match()

    def del_player(self, player: Union[str, int]) -> None:
        """Remove a player from the call-up.

        :param player_name: Name of the player who wants to leave.

        """
        self._players.leave(player)
        self._match = None

        if self._players.are_ready():
            self.create_match()

    def set_maximum(self, maximum: Optional[int]) -> None:
        """Set the maximum number of players.

        :param maximum: The number of players.

        """
        self._players.maximum = maximum

    def create_match(self) -> None:
        """Create a new match."""
        self._match = Match.auto_create(self._players)

    def set_results(self, results: PlayersStatInput) -> None:
        """Introduce the results of the match.

        :param results: The results object.

        """
        if self._match is None:
            raise CallUpMatchNotYetCreatedError(
                "The match hasn't been created yet, so no results can be set"
            )

        self._match.set_results(results, self._date)

    def __str__(self) -> str:
        return self.as_yaml()

    def as_yaml(self) -> str:
        """Obtain the YAML representation of the call-up.

        :returns: The YAML string.

        """
        call_up_info = yaml.dump(
            {
                "convocatoria": f"*{self._date.strftime('%A %d/%b/%Y %H:%M')}*",
                "localización": f"*{self._location}*",
            },
            allow_unicode=True,
            indent=4,
            sort_keys=False,
        )

        search_info: str = ""
        if self.is_searching():
            search_info = yaml.dump(
                {"búsqueda": self.subs_chat.message_id},
                allow_unicode=True,
                indent=4,
            )
            search_info = f"\n{search_info}"

        match_info: str = ""
        if self._match is not None:
            match_info = self.match.as_yaml()

        version_info = yaml.dump(
            {"versión": __version__},
            allow_unicode=True,
            indent=4,
        )

        return f"{call_up_info}{self.players.as_yaml()}{search_info}{match_info}{version_info}"

    @staticmethod
    def from_yaml(yaml_str: str, main_chat_id: int, main_chat_msg: int) -> "CallUp":
        """Create a CallUp object from a yaml string and the chat and messaages ids.

        :param yaml_str: The text containing the yaml call-up.
        :param main_chat_id: The call-up chat.
        :param main_chat_msg: The call-up message.
        :returns: The newly created object.

        """
        call_up_info: dict = yaml.safe_load(yaml_str)

        if "finalizado" in call_up_info:
            raise CallUpMatchAlreadyFinishedError()

        try:
            del call_up_info["versión"]
            date = datetime.datetime.strptime(
                call_up_info.pop("convocatoria"), "%A %d/%b/%Y %H:%M"
            )
            subs_chat_msg = call_up_info.pop("búsqueda", None)
            location = call_up_info.pop("localización")
            players = Players.from_list(call_up_info.pop("jugadores"))
            match: Optional[Match] = None
            if len(call_up_info) >= 2:
                match = Match.from_dict(call_up_info)

            return CallUp(
                date=date,
                main_chat_id=main_chat_id,
                main_chat_msg=main_chat_msg,
                subs_chat_msg=subs_chat_msg,
                location=location,
                players=players,
                match=match,
            )
        except KeyError as error:
            raise CallUpWrongFormatError(error.args[0])
