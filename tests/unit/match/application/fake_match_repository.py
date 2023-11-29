import datetime
import uuid

from typing import Optional

from pyball.greenfield.match.domain.matches import Matches
from pyball.greenfield.match.domain.model.match import Match


class FakeMatchRepository(Matches):
    def __init__(self) -> None:
        self.matches = {}

    def save(self, match: Match) -> None:
        self.matches[match.id] = match

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self.matches.get(id)

    def get_by_date(self, date: datetime.datetime) -> Optional[Match]:
        for match in self.matches.values():
            if match.date == date:
                return match

        return None
