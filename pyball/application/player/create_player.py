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
"""Create player use case."""

from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player
from pyball.domain.player.repository import PlayerRepository


class CreatePlayer:
    """Use case for creating a new player."""

    def __init__(self, player_repository: PlayerRepository):
        """Initialize with a player repository."""
        self.player_repository = player_repository

    def execute(self, name: str, group: str, position: str | None = None) -> Player:
        """Create a new player with the given name, group, and optional position."""
        existing = self.player_repository.find_all()
        if any(p.name.lower() == name.lower() for p in existing):
            raise PlayerAlreadyExistsError(name)

        player = Player.create(name=name, group=group, position=position)
        self.player_repository.save(player)
        return player
