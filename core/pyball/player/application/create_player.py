# Copyright (c) 2023 Luis Liñán
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

"""Create a new player use case."""

import uuid

from pyball.player.domain.errors import PlayerIdIsAlreadyInUse, PlayerNameIsAlreadyInUse
from pyball.player.domain.model.player import Player
from pyball.player.domain.players import Players


class CreatePlayer:
    def __init__(self, players: Players) -> None:
        self._players = players

    def create(self, id: uuid.UUID, name: str, main: bool = False) -> None:
        if self._players.get(id) is not None:
            raise PlayerIdIsAlreadyInUse(id)

        if self._players.get_by_name(name) is not None:
            raise PlayerNameIsAlreadyInUse(name)

        player = Player(id=id, name=name, main=main)
        self._players.save(player)
