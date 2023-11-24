import datetime
import uuid

from typing import Optional
from unittest import TestCase

import faker
from pyball.greenfield.player.application.create_player import CreatePlayer

# from pyball.greenfield.player.application.create_player import CreatePlayer
# from pyball.greenfield.player.domain.errors import DateAlreadyUsedError, MatchAlreadyExistentError
from pyball.greenfield.player.domain.players import Players
from pyball.greenfield.player.domain.model.player import Player

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



class TestCreatePlayer(TestCase):
    def test_player_is_created(self) -> None:
        # Arrange
        fake_player_respository = FakePlayerRepository()
        create_player = CreatePlayer(fake_player_respository)
        fake_uuid = uuid.uuid4()
        fake_name = fake.unique.user_name()

        # Act
        create_player.create(id=fake_uuid, name=fake_name)

        # Assert
        obtained_player = fake_player_respository.get(fake_uuid)
        self.assertIsNotNone(obtained_player)
        self.assertEqual(fake_uuid, obtained_player.id)
        self.assertEqual(fake_name, obtained_player.name)

    def test_exception_is_raised_when_player_already_exists(self) -> None:
        pass
