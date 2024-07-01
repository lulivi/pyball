import datetime
import uuid

from typing import Dict, Optional

from pyball.match.domain.matches import Matches
from pyball.match.domain.model.match import Match


class FakeMatchRepository(Matches):
    def __init__(self) -> None:
        self.matches: Dict[Match] = {}

    def save(self, match: Match) -> None:
        self.matches[match.id] = match

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self.matches.get(id)
