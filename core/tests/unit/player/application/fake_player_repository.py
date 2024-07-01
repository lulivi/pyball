import datetime
import uuid

from typing import Optional

import faker

from pyball.player.domain.model.player import Player
from pyball.player.domain.players import Players

fake: faker.Faker = faker.Faker()


class FakePlayerRepository(Players):
    def __init__(self) -> None:
        self.players = {}

    def save(self, player: Player) -> None:
        self.players[player.id] = player

    def get(self, id: uuid.UUID) -> Optional[Player]:
        return self.players.get(id)

    def get_by_name(self, name: str) -> Optional[Player]:
        for player in self.players.values():
            if player.name == name:
                return player

        return None
