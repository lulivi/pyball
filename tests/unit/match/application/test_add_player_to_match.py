import uuid

from unittest import TestCase

import faker

from pyball.greenfield.match.application.add_player_to_match import AddPlayerToMatch
from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.application.errors import MatchIdNotFound, PlayerIsAlreadyInMatch
from pyball.greenfield.player.application.create_player import CreatePlayer
from tests.unit.match.application.fake_match_repository import FakeMatchRepository
from tests.unit.player.application.fake_player_repository import FakePlayerRepository

fake: faker.Faker = faker.Faker()


class TestAddPlayerToMatch(TestCase):
    def test_it_should_add_player_to_match(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).create(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_match_repository = FakeMatchRepository()
        fake_match_uuid = uuid.uuid4()
        CreateMatch(fake_match_repository).create(
            id=fake_match_uuid,
            date_time=fake.unique.date_time(),
            location=fake.unique.user_name(),
        )

        # Act
        AddPlayerToMatch(fake_match_repository).add(
            match_id=fake_match_uuid,
            player_id=fake_player_uuid,
        )

        # Assert
        self.assertTrue(fake_player_uuid in fake_match_repository.get(fake_match_uuid))

    def test_it_should_raise_an_error_if_the_match_is_not_found(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).create(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_match_repository = FakeMatchRepository()
        fake_match_uuid = uuid.uuid4()

        # Assert
        with self.assertRaises(MatchIdNotFound) as cm:
            # Act
            AddPlayerToMatch(fake_match_repository).add(
                match_id=fake_match_uuid,
                player_id=fake_player_uuid,
            )

        self.assertEqual(cm.exception.id, fake_match_uuid)

    def test_it_should_raise_an_error_if_player_already_in_match(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).create(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_match_repository = FakeMatchRepository()
        fake_match_uuid = uuid.uuid4()
        CreateMatch(fake_match_repository).create(
            id=fake_match_uuid,
            date_time=fake.unique.date_time(),
            location=fake.unique.user_name(),
        )
        AddPlayerToMatch(fake_match_repository).add(
            match_id=fake_match_uuid,
            player_id=fake_player_uuid,
        )

        # Assert
        with self.assertRaises(PlayerIsAlreadyInMatch) as cm:
            # Act
            AddPlayerToMatch(fake_match_repository).add(
                match_id=fake_match_uuid,
                player_id=fake_player_uuid,
            )

        self.assertEqual(cm.exception.player_id, fake_player_uuid)
