import datetime
import uuid


class MatchNotFoundError(Exception):
    """The match was not found in the repository."""


class MatchAlreadyExistentError(Exception):
    """There is a match with the same UUID or date in the repository."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The match id `{id}` is already in use"
        super().__init__(self.message)


class DateAlreadyUsedError(Exception):
    """There is a match with the same UUID or date in the repository."""

    def __init__(self, date: datetime.datetime) -> None:
        self.date = date
        self.message = f"The date `{date}` is already in use"
        super().__init__(self.message)
