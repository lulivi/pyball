"""Player repository interface."""

from typing import Protocol

from pyball.domain.player.models import Player, PlayerId


class PlayerRepository(Protocol):
    """Repository interface for Player aggregate."""

    def save(self, player: Player) -> None:
        ...

    def find_by_id(self, player_id: PlayerId) -> Player | None:
        ...

    def find_by_name(self, name: str) -> Player | None:
        ...

    def find_all(self) -> list[Player]:
        ...

    def delete(self, player_id: PlayerId) -> None:
        ...
