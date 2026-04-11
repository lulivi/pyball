"""Player repository interface."""

from typing import Protocol

from pyball.domain.player.models import Player, PlayerId


class PlayerRepository(Protocol):
    """Repository interface for Player aggregate."""

    def save(self, player: Player) -> None:
        """Save a player to the repository."""

    def find_by_id(self, player_id: PlayerId) -> Player | None:
        """Find a player by their ID."""

    def find_by_name(self, name: str) -> Player | None:
        """Find a player by their name."""

    def find_all(self) -> list[Player]:
        """Return all players."""

    def delete(self, player_id: PlayerId) -> None:
        """Delete a player by their ID."""
