import uuid

from pyball.meetup.domain.player_checker import IPlayerChecker
from pyball.player.domain.players import Players
from pyball.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository


class PlayerChecker(IPlayerChecker):
    def __init__(self) -> None:
        self._players = PlayerSqlitoRepository()

    def check_player_exists(self, player_id: uuid.UUID) -> bool:
        return self._players.get(id=player_id) is not None
