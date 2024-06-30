import uuid

from typing import List, Optional

from pyball.player.domain.model.player import Player
from pyball.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository


class GetPlayer:
    def __init__(self) -> None:
        self._players = PlayerSqlitoRepository()

    def all(self) -> List[Player]:
        return self._players.all()

    def by_id(self, id: uuid.UUID) -> Optional[Player]:
        return self._players.get(id=id)

    def by_name(self, name: str) -> Optional[Player]:
        return self._players.get_by_name(name=name)
