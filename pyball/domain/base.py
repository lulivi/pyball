"""Base classes for domain objects."""

from typing import Generic, TypeVar

T = TypeVar("T")


class ValueObject:
    """Base class for value objects."""

    def __eq__(self, other: object) -> bool:
        """Check equality based on all attributes."""
        if not isinstance(other, self.__class__):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        """Calculate hash based on all attributes."""
        return hash(self.as_tuple())

    def as_tuple(self) -> tuple:
        """Return attributes as a tuple for hashing and equality."""
        return tuple(getattr(self, name) for name in self.__annotations__)


class Entity(Generic[T]):
    """Base class for entities with identity."""

    id: T

    def __eq__(self, other: object) -> bool:
        """Check equality based on entity identity."""
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Calculate hash based on entity identity."""
        return hash(self.id)

    def __setattr__(self, name, value):
        """Prevent modification of the entity ID."""
        if name == "id" and hasattr(self, "id"):
            raise AttributeError("Entity.id cannot be modified after construction")
        object.__setattr__(self, name, value)
