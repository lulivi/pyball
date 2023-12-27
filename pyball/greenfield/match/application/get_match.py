import datetime
import uuid

from pyball.greenfield.match.application.errors import MatchDateNotFound, MatchIdNotFound
from pyball.greenfield.match.domain.matches import Matches
from pyball.greenfield.match.domain.model.match import Match


class GetMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def by_id(self, id: uuid.UUID) -> Match:
        match = self._matches.get(id=id)

        if match is None:
            raise MatchIdNotFound(id=id)

        return match

    def by_date(self, date: datetime.datetime) -> Match:
        match = self._matches.get_by_date(date=date)

        if match is None:
            raise MatchDateNotFound(date=date)

        return match
