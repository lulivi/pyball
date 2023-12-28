import uuid

from unittest import TestCase

import faker

from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.application.errors import MatchDateNotFound, MatchIdNotFound
from pyball.greenfield.match.application.get_match import GetMatch
from tests.unit.match.application.fake_match_repository import FakeMatchRepository

fake: faker.Faker = faker.Faker()


class TestGetMatch(TestCase):
    def test_it_should_return_a_match_by_id(self) -> None:
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_date_time = fake.unique.date_time()
        fake_location = fake.unique.user_name()
        fake_match_respository = FakeMatchRepository()
        CreateMatch(fake_match_respository).create(
            id=fake_uuid,
            date_time=fake_date_time,
            location=fake_location,
        )

        # Act
        obtained_match = GetMatch(fake_match_respository).by_id(id=fake_uuid)

        # Assert
        self.assertEqual(obtained_match.id, fake_uuid)
        self.assertEqual(obtained_match.date_time, fake_date_time)
        self.assertEqual(obtained_match.location, fake_location)

    def test_it_should_raise_an_exception_when_match_is_not_found_by_id(self):
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_match_respository = FakeMatchRepository()

        # Assert
        with self.assertRaises(MatchIdNotFound) as cm:
            # Act
            GetMatch(fake_match_respository).by_id(fake_uuid)

        self.assertEqual(cm.exception.id, fake_uuid)

    def test_it_should_return_a_match_by_date(self) -> None:
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_date_time = fake.unique.date_time()
        fake_location = fake.unique.user_name()
        fake_match_respository = FakeMatchRepository()
        CreateMatch(fake_match_respository).create(
            id=fake_uuid,
            date_time=fake_date_time,
            location=fake_location,
        )

        # Act
        obtained_match = GetMatch(fake_match_respository).by_date(fake_date_time)

        # Assert
        self.assertEqual(obtained_match.id, fake_uuid)
        self.assertEqual(obtained_match.date_time, fake_date_time)
        self.assertEqual(obtained_match.location, fake_location)

    def test_it_should_raise_an_exception_when_match_is_not_found_by_date(self) -> None:
        # Arrange
        fake_date_time = fake.unique.date_time()
        fake_match_respository = FakeMatchRepository()

        # Assert
        with self.assertRaises(MatchDateNotFound) as cm:
            # Act
            GetMatch(fake_match_respository).by_date(fake_date_time)

        self.assertEqual(cm.exception.date_time, fake_date_time)
