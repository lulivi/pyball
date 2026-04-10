"""Base classes for domain objects."""

from typing import Generic, TypeVar
from uuid import uuid4

T = TypeVar("T")


class ValueObject:
    """Base class for value objects."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def as_tuple(self) -> tuple:
        """Return attributes as a tuple for hashing and equality."""
        return tuple(getattr(self, name) for name in self.__annotations__)


class Entity(Generic[T]):
    """Base class for entities with identity."""

    id: T

    def __init__(self, entity_id: T | None = None) -> None:
        object.__setattr__(self, "id", entity_id or uuid4())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __setattr__(self, name, value):
        if name == "id" and hasattr(self, "id"):
            raise AttributeError("Entity.id cannot be modified after construction")
        object.__setattr__(self, name, value)
