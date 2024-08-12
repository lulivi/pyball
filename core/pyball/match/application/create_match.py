import uuid

from typing import List

from pyball.match.domain.errors import MatchAlreadyExistsError
from pyball.match.domain.matches import Matches
from pyball.match.domain.model.match import Match


class CreateMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def execute(
        self,
        match_id: uuid.UUID,
        meetup_id: uuid.UUID,
        local_team: List[uuid.UUID],
        visiting_team: List[uuid.UUID],
    ) -> None:
        if self._matches.get(match_id) is not None:
            raise MatchAlreadyExistsError(match_id)

        my_match = Match(match_id, meetup_id, local_team, visiting_team)
        self._matches.save(my_match)
