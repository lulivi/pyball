import datetime
import uuid


class MatchIdNotFound(Exception):
    """The match was not found."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"There is no match with the id `{id}` does not exist"
        super().__init__(self.message)


class MatchDateNotFound(Exception):
    """The match was not found."""

    def __init__(self, date: datetime.datetime) -> None:
        self.date = date
        self.message = f"There is no match with the date `{date}` does not exist"
        super().__init__(self.message)
