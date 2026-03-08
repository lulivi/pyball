import uuid

from pyball.meetup.domain.player_checker import IPlayerChecker
from pyball.player.domain.players import Players
from pyball.player.infrastructure.player_json_repository import PlayerJsonRepository


class PlayerChecker(IPlayerChecker):
    def __init__(self) -> None:
        self._players = PlayerJsonRepository()

    def check_player_exists(self, player_id: uuid.UUID) -> bool:
        return self._players.get(id=player_id) is not None
