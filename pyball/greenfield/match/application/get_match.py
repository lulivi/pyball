import uuid

from pyball.greenfield.match.domain.matches import Matches
from pyball.greenfield.match.domain.model.match import Match


class GetMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def get(self, id: uuid.UUID) -> Match:
        match = self._matches.get(id=id)

        return match
