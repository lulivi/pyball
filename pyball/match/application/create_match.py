import datetime
import uuid

from pyball.match.domain.errors import DateAlreadyUsedError, MatchAlreadyExistentError
from pyball.match.domain.matches import Matches
from pyball.match.domain.model.match import Match


class CreateMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def create(self, id: uuid.UUID, date: datetime.datetime, location: str) -> None:
        if self._matches.get(id=id) is not None:
            raise MatchAlreadyExistentError(id=id)

        if self._matches.get_by_date(date=date) is not None:
            raise DateAlreadyUsedError(date=date)

        match = Match(id=id, date=date, location=location)
        self._matches.save(match)
