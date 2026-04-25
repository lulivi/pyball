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
