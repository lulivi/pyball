"""Delete player use case."""

from pyball.domain.player.errors import PlayerNotFoundError
from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class DeletePlayer:
    """Use case for deleting a player."""

    def __init__(self, player_repository: PlayerRepository):
        """Initialize with a player repository."""
        self.player_repository = player_repository

    def execute(self, player_id: str) -> None:
        """Delete a player by their ID."""
        parsed_id = PlayerId.from_string(player_id)

        player = self.player_repository.find_by_id(parsed_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        self.player_repository.delete(parsed_id)
