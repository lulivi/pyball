"""Create player use case."""

from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player
from pyball.domain.player.repository import PlayerRepository


class CreatePlayer:
    """Use case for creating a new player."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, name: str) -> Player:
        existing = self.player_repository.find_by_name(name)
        if existing:
            raise PlayerAlreadyExistsError(name)
        player = Player.create(name)
        self.player_repository.save(player)
        return player
