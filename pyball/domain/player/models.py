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
"""Player models."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from pyball.domain.base import Entity, ValueObject
from pyball.domain.player.errors import InvalidPlayerIdError


VALID_POSITIONS = ("portero", "defensa", "centrocampista", "delantero")


@dataclass
class Player(Entity["PlayerId"]):
    """Player entity."""

    id: PlayerId
    name: str
    group: str
    position: str | None = None

    def __post_init__(self):
        """Validate player attributes after initialization."""
        if not self.name:
            raise ValueError("Player name cannot be empty")
        if self.group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        if self.position is not None and self.position not in VALID_POSITIONS:
            raise ValueError(f"Player position must be one of {VALID_POSITIONS} or None")

    @classmethod
    def create(cls, name: str, group: str = "regular", position: str | None = None) -> "Player":
        """Create a new player with the given name, group, and optional position."""
        return cls(
            id=PlayerId.generate(),
            name=name.strip() if name else "",
            group=group,
            position=position,
        )

    def rename(self, new_name: str) -> None:
        """Rename the player to a new name."""
        if not new_name or not new_name.strip():
            raise ValueError("Player name cannot be empty")
        self.name = new_name.strip()

    def set_group(self, new_group: str) -> None:
        """Set the player's group to regular or substitute."""
        if new_group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        self.group = new_group

    def set_position(self, new_position: str | None) -> None:
        """Set the player's position, or clear it with None."""
        if new_position is not None and new_position not in VALID_POSITIONS:
            raise ValueError(f"Player position must be one of {VALID_POSITIONS} or None")
        self.position = new_position


@dataclass(frozen=True)
class PlayerId(ValueObject):
    """Value object for player identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "PlayerId":
        """Create a PlayerId from a string UUID."""
        try:
            return cls(UUID(value))
        except ValueError as e:
            raise InvalidPlayerIdError(value) from e

    @classmethod
    def generate(cls) -> "PlayerId":
        """Generate a new random PlayerId."""
        return cls(uuid4())
