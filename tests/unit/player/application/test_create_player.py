import datetime
import uuid

from typing import Optional
from unittest import TestCase

import faker

from pyball.greenfield.player.application.create_player import CreatePlayer
from pyball.greenfield.player.domain.errors import (
    PlayerNameAlreadyInUseError,
    PlayerUuidAlreadyExistsError,
)
from pyball.greenfield.player.domain.model.player import Player
from pyball.greenfield.player.domain.players import Players
from tests.unit.player.application.fake_player_repository import FakePlayerRepository

fake: faker.Faker = faker.Faker()


class TestCreatePlayer(TestCase):
    def test_player_is_created(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        create_player = CreatePlayer(fake_player_repository)
        fake_uuid = uuid.uuid4()
        fake_name = fake.unique.user_name()

        # Act
        create_player.create(id=fake_uuid, name=fake_name)

        # Assert
        obtained_player = fake_player_repository.get(fake_uuid)
        self.assertIsNotNone(obtained_player)
        self.assertEqual(fake_uuid, obtained_player.id)
        self.assertEqual(fake_name, obtained_player.name)

    def test_exception_is_raised_when_player_uuid_already_exists(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        create_player = CreatePlayer(fake_player_repository)
        fake_uuid = uuid.uuid4()
        create_player.create(fake_uuid, fake.unique.user_name())

        # Assert
        with self.assertRaises(PlayerUuidAlreadyExistsError) as cm:
            # Act
            create_player.create(fake_uuid, fake.unique.user_name())

        self.assertEqual(cm.exception.id, fake_uuid)

    def test_exception_is_raised_when_player_name_already_in_use(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        create_player = CreatePlayer(fake_player_repository)
        fake_name = fake.unique.user_name()
        create_player.create(uuid.uuid4(), fake_name)

        # Assert
        with self.assertRaises(PlayerNameAlreadyInUseError) as cm:
            # Act
            create_player.create(uuid.uuid4(), fake_name)

        self.assertEqual(cm.exception.name, fake_name)
