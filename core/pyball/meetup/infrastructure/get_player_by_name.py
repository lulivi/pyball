from typing import Optional

from pyball.greenfield.player.domain.model.player import Player
from pyball.greenfield.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository


class GetPlayer:
    def __init__(self) -> None:
        self._players = PlayerSqlitoRepository()

    def by_name(self, name: str) -> Optional[Player]:
        return self._players.get_by_name(name=name)
