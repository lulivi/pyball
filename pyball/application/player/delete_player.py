"""Delete player use case."""

from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class DeletePlayer:
    """Use case for deleting a player."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player_id: str) -> None:
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            from pyball.domain.player.errors import PlayerNotFoundError
            raise PlayerNotFoundError(player_id)
        self.player_repository.delete(PlayerId.from_string(player_id))
