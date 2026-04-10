from pyball.domain.player.errors import PlayerNotFoundError
from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class ChangePlayerGroup:
    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player_id: str, new_group: str) -> Player:
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            raise PlayerNotFoundError(player_id)

        player.set_group(new_group)
        self.player_repository.save(player)
        return player
