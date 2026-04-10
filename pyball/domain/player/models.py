"""Player models."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from pyball.domain.base import Entity, ValueObject
from pyball.domain.player.errors import InvalidPlayerIdError


@dataclass(frozen=True)
class PlayerId(ValueObject):
    """Value object for player identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "PlayerId":
        try:
            return cls(UUID(value))
        except ValueError as e:
            raise InvalidPlayerIdError(value) from e

    @classmethod
    def generate(cls) -> "PlayerId":
        return cls(uuid4())


@dataclass
class Player(Entity):
    """Player entity."""

    id: PlayerId
    name: str
    group: str

    def __post_init__(self):
        if not self.name:
            raise ValueError("Player name cannot be empty")
        if self.group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")

    @classmethod
    def create(cls, name: str, group: str = "regular") -> "Player":
        if not name or not name.strip():
            raise ValueError("Player name cannot be empty")
        if group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        return cls(id=PlayerId.generate(), name=name.strip(), group=group)

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("Player name cannot be empty")
        object.__setattr__(self, "name", new_name.strip())

    def set_group(self, new_group: str) -> None:
        if new_group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        object.__setattr__(self, "group", new_group)
