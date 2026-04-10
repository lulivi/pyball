"""Change player group use case."""

from pyball.domain.player.errors import PlayerNotFoundError
from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class ChangePlayerGroup:
    """Use case for changing a player's group."""

    def __init__(self, player_repository: PlayerRepository):
        """Initialize with a player repository."""
        self.player_repository = player_repository

    def execute(self, player_id: str, new_group: str) -> Player:
        """Change a player's group to regular or substitute."""
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            raise PlayerNotFoundError(player_id)

        player.set_group(new_group)
        self.player_repository.save(player)
        return player
