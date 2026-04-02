"""Base classes for domain objects."""

from uuid import UUID, uuid4


class ValueObject:
    """Base class for value objects."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def as_tuple(self) -> tuple:
        return tuple(getattr(self, name) for name in self.__annotations__)


class Entity:
    """Base class for entities with identity."""

    id: UUID

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
