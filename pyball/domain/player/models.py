"""Player models."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from pyball.domain.base import Entity, ValueObject


@dataclass(frozen=True)
class PlayerId(ValueObject):
    """Value object for player identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "PlayerId":
        return cls(UUID(value))

    @classmethod
    def generate(cls) -> "PlayerId":
        return cls(uuid4())


@dataclass
class Player(Entity):
    """Player entity."""

    id: PlayerId
    name: str

    @classmethod
    def create(cls, name: str) -> "Player":
        if not name or not name.strip():
            raise ValueError("Player name cannot be empty")
        return cls(id=PlayerId.generate(), name=name.strip())

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("Player name cannot be empty")
        self.name = new_name.strip()
