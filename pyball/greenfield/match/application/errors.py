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


class PlayerIsAlreadyInMatch(Exception):
    """The player is already in the match."""

    def __init__(self, match_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.match_id = match_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is already in the match `{match_id}`"
        super().__init__(self.message)
