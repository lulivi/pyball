import datetime
import uuid

from typing import List


class Match:
    def __init__(self, id: uuid.UUID, date: datetime.datetime, location: str):
        if not isinstance(id, uuid.UUID):
            raise AttributeError("The uuid is not a UUID object")
        self._id: uuid.UUID = id
        self._date: datetime.datetime = date
        self._location: str = location
        self._players: List[uuid.UUID] = []

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def location(self) -> str:
        return self._location

    @property
    def players(self) -> List[uuid.UUID]:
        return self._players

    def add_player(self, id: uuid.UUID) -> None:
        self._players.append(id)

    def __contains__(self, player: uuid.UUID) -> bool:
        return player in self._players
