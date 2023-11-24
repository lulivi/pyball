import datetime
import uuid


class Match:
    def __init__(self, id: uuid.UUID, date: datetime.datetime, location: str):
        if not isinstance(id, uuid.UUID):
            raise AttributeError("The uuid is not a UUID object")
        self._id: uuid.UUID = id
        self._date: datetime.datetime = date
        self._location: str = location

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def date(self) -> datetime.datetime:
        return self._date

    @property
    def location(self) -> str:
        return self._location
