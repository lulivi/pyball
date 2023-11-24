

import uuid
from pyball.greenfield.player.domain.model.player import Player
from pyball.greenfield.player.domain.players import Players


class CreatePlayer:

    def __init__(self, players: Players) -> None:
        self._players = players

    def create(self, id: uuid.UUID, name: str) -> None:
        player = Player(id=id, name=name)
        self._players.save(player)
