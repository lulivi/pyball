import datetime
import uuid

from dataclasses import dataclass
from typing import Any, List, Tuple


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
