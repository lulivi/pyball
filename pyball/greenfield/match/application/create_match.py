import uuid

from typing import List


class CreateMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def create(
        self,
        match_id: uuid.UUID,
        meetup_id: uuid.UUID,
        local_team: List[uuid.UUID],
        visiting_team: List[uuid.UUID],
    ) -> None:
        pass
