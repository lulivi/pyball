import datetime
import logging
import uuid

from dataclasses import dataclass
from typing import Any, List, Tuple

from pyballbot.settings import DISPLAY_DATETIME_FORMAT

logger = logging.getLogger(__name__)


@dataclass
class Response:
    status: int
    json: Any


@dataclass
class Meetup:
    id: uuid.UUID
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...]
    players: List[uuid.UUID]
    teams: List[List[uuid.UUID]]

    @staticmethod
    def from_json(json_meetup: dict) -> "Meetup":
        return Meetup(
            id=json_meetup["id"],
            date_time=datetime.datetime.fromisoformat(json_meetup["date_time"]),
            location=json_meetup["location"],
            possible_team_sizes=tuple(json_meetup["possible_team_sizes"]),
            players=json_meetup["players"],
            teams=json_meetup["teams"],
        )


@dataclass
class Player:
    id: uuid.UUID
    name: str
    main: bool = False

    @staticmethod
    def from_json(json_player: dict) -> "Player":
        return Player(
            id=json_player["id"],
            name=json_player["name"],
            main=json_player["main"],
        )


@dataclass
class DisplayMeetup:
    date_time: datetime.datetime
    location: str
    players: List[Player]
    teams: List[List[Player]]

    def to_string(self, classified: bool = False) -> str:
        message = (
            f"Fecha: {self.date_time.strftime(DISPLAY_DATETIME_FORMAT)}\nLocalización:"
            f" {self.location}"
        )

        if self.players:
            message = f"{message}\n\nAsistentes:"
            for player in self.players:
                string_player = player.name
                if player.main and classified:
                    string_player = "?????"
                message = f"{message}\n- {string_player}"

        if self.teams:
            message = f"{message}\n\nEquipos:"
            team_number = 0
            for team in self.teams:
                message = f"{message}\n- Equipo {team_number}:"
                for player in team:
                    string_player = player.name
                    if player.main and classified:
                        string_player = "?????"
                    message = f"{message}\n  - {string_player}"
                team_number += 1

        return message
