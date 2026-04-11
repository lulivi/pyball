"""Rename player use case."""

from pyball.domain.player.errors import NameAlreadyTakenError, PlayerNotFoundError
from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class RenamePlayer:
    """Use case for renaming a player."""

    def __init__(self, player_repository: PlayerRepository):
        """Initialize with a player repository."""
        self.player_repository = player_repository

    def execute(self, player_id: str, new_name: str) -> Player:
        """Rename a player to a new name."""
        parsed_id = PlayerId.from_string(player_id)

        player = self.player_repository.find_by_id(parsed_id)
        if not player:
            raise PlayerNotFoundError(player_id)

        existing = self.player_repository.find_by_name(new_name)
        if existing and existing.id != player.id:
            raise NameAlreadyTakenError(new_name)

        player.rename(new_name)
        self.player_repository.save(player)
        return player
