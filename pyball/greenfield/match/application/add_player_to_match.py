import uuid

from pyball.greenfield.match.application.errors import MatchIdNotFound, PlayerIsAlreadyInMatch
from pyball.greenfield.match.domain.matches import Matches


class AddPlayerToMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def add(self, match_id: uuid.UUID, player_id: uuid.UUID) -> None:
        match = self._matches.get(id=match_id)

        if match is None:
            raise MatchIdNotFound(id=match_id)

        if player_id in match:
            raise PlayerIsAlreadyInMatch(match_id=match_id, player_id=player_id)

        match.add_player(id=player_id)
        self._matches.save(match=match)
