import uuid

from unittest import TestCase

import faker

from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.domain.errors import DateAlreadyUsedError, MatchAlreadyExistentError
from tests.unit.match.application.fake_match_repository import FakeMatchRepository

fake: faker.Faker = faker.Faker()


class TestCreateMatch(TestCase):
    def test_match_is_created(self) -> None:
        # Arrange
        fake_match_respository = FakeMatchRepository()
        fake_uuid = uuid.uuid4()
        fake_date = fake.unique.date_time()
        fake_location = fake.unique.user_name()

        # Act
        CreateMatch(fake_match_respository).create(id=fake_uuid, date=fake_date, location=fake_location)

        # Assert
        obtained_match = fake_match_respository.get(fake_uuid)
        self.assertIsNotNone(obtained_match)
        self.assertEqual(fake_uuid, obtained_match.id)
        self.assertEqual(fake_date, obtained_match.date)
        self.assertEqual(fake_location, obtained_match.location)

    def test_exception_is_raised_when_match_already_exists(self) -> None:
        # Arrange
        create_match = CreateMatch(FakeMatchRepository())
        fake_uuid = uuid.uuid4()
        create_match.create(
            id=fake_uuid, date=fake.unique.date_time(), location=fake.unique.user_name()
        )

        # Assert
        with self.assertRaises(MatchAlreadyExistentError) as cm:
            # Act
            create_match.create(
                id=fake_uuid, date=fake.unique.date_time(), location=fake.unique.user_name()
            )

        self.assertEqual(cm.exception.id, fake_uuid)

    def test_exception_is_raised_when_match_date_already_in_use(self) -> None:
        # Arrange
        create_match = CreateMatch(FakeMatchRepository())
        fake_date = fake.unique.date_time()
        create_match.create(
            id=uuid.uuid4(), date=fake_date, location=fake.unique.user_name()
        )

        # Assert
        with self.assertRaises(DateAlreadyUsedError) as cm:
            # Act
            create_match.create(id=uuid.uuid4(), date=fake_date, location=fake.unique.user_name())

        self.assertEqual(cm.exception.date, fake_date)
