import datetime
import uuid

from typing import Dict, Optional

from pyball.greenfield.match.domain.matches import Matches
from pyball.greenfield.match.domain.model.match import Match


class FakeMatchRepository(Matches):
    def __init__(self) -> None:
        self.matches: Dict[Match] = {}

    def save(self, match: Match) -> None:
        self.matches[match.id] = match

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self.matches.get(id)

    def get_by_date(self, date_time: datetime.datetime) -> Optional[Match]:
        for match in self.matches.values():
            if match.date_time == date_time:
                return match

        return None
