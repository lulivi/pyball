# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
