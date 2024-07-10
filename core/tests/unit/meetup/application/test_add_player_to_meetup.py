import uuid

from unittest import TestCase

import faker

from pyball.meetup.application.add_player_to_meetup import AddPlayerToMeetup
from pyball.meetup.application.create_meetup import CreateMeetup
from pyball.meetup.application.errors import MeetupIdNotFound, PlayerIsAlreadyInMeetup
from pyball.player.application.create_player import CreatePlayer
from tests.unit.meetup.application.fake_meetup_repository import FakeMeetupRepository
from tests.unit.player.application.fake_player_repository import FakePlayerRepository

fake: faker.Faker = faker.Faker()


class TestAddPlayerToMeetup(TestCase):
    def test_it_should_add_player_to_meetup(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).execute(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_meetup_repository = FakeMeetupRepository()
        fake_meetup_uuid = uuid.uuid4()
        CreateMeetup(fake_meetup_repository).create(
            id=fake_meetup_uuid,
            date_time=fake.unique.date_time(),
            location=fake.unique.user_name(),
        )

        # Act
        AddPlayerToMeetup(fake_meetup_repository).add(
            meetup_id=fake_meetup_uuid,
            player_id=fake_player_uuid,
        )

        # Assert
        self.assertTrue(fake_player_uuid in fake_meetup_repository.get(fake_meetup_uuid))

    def test_it_should_raise_an_error_if_the_meetup_is_not_found(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).execute(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_meetup_repository = FakeMeetupRepository()
        fake_meetup_uuid = uuid.uuid4()

        # Assert
        with self.assertRaises(MeetupIdNotFound) as cm:
            # Act
            AddPlayerToMeetup(fake_meetup_repository).add(
                meetup_id=fake_meetup_uuid,
                player_id=fake_player_uuid,
            )

        self.assertEqual(cm.exception.id, fake_meetup_uuid)

    def test_it_should_raise_an_error_if_player_already_in_meetup(self) -> None:
        # Arrange
        fake_player_repository = FakePlayerRepository()
        fake_player_uuid = uuid.uuid4()
        CreatePlayer(fake_player_repository).execute(
            id=fake_player_uuid,
            name=fake.unique.user_name(),
        )
        fake_meetup_repository = FakeMeetupRepository()
        fake_meetup_uuid = uuid.uuid4()
        CreateMeetup(fake_meetup_repository).create(
            id=fake_meetup_uuid,
            date_time=fake.unique.date_time(),
            location=fake.unique.user_name(),
        )
        AddPlayerToMeetup(fake_meetup_repository).add(
            meetup_id=fake_meetup_uuid,
            player_id=fake_player_uuid,
        )

        # Assert
        with self.assertRaises(PlayerIsAlreadyInMeetup) as cm:
            # Act
            AddPlayerToMeetup(fake_meetup_repository).add(
                meetup_id=fake_meetup_uuid,
                player_id=fake_player_uuid,
            )

        self.assertEqual(cm.exception.player_id, fake_player_uuid)
