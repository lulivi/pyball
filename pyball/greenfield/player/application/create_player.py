import uuid

from pyball.greenfield.player.domain.errors import (
    PlayerNameAlreadyInUseError,
    PlayerUuidAlreadyExistsError,
)
from pyball.greenfield.player.domain.model.player import Player
from pyball.greenfield.player.domain.players import Players


class CreatePlayer:
    def __init__(self, players: Players) -> None:
        self._players = players

    def create(self, id: uuid.UUID, name: str) -> None:
        if self._players.get(id) is not None:
            raise PlayerUuidAlreadyExistsError(id)

        if self._players.get_by_name(name) is not None:
            raise PlayerNameAlreadyInUseError(name)

        player = Player(id=id, name=name)
        self._players.save(player)
