from unittest import TestCase
import uuid

from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.application.errors import MatchIdNotFound
from pyball.greenfield.match.application.get_match import GetMatch
from tests.unit.match.application.fake_match_repository import FakeMatchRepository

import faker

fake: faker.Faker = faker.Faker()


class TestGetMatch(TestCase):
    def test_match_is_returned(self) -> None:
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_date = fake.unique.date_time()
        fake_location = fake.unique.user_name()
        fake_match_respository = FakeMatchRepository()
        CreateMatch(fake_match_respository).create(
            id=fake_uuid,
            date=fake_date,
            location=fake_location,
        )

        # Act
        obtained_match = GetMatch(fake_match_respository).get(id=fake_uuid)

        # Assert
        self.assertEqual(obtained_match.id, fake_uuid)
        self.assertEqual(obtained_match.date, fake_date)
        self.assertEqual(obtained_match.location, fake_location)

    def test_exception_is_raised_when_match_is_not_found(self):
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_match_respository = FakeMatchRepository()

        # Assert
        with self.assertRaises(MatchIdNotFound) as cm:
            # Act
            GetMatch(fake_match_respository).get(fake_uuid)

        self.assertEqual(cm.exception.id, fake_uuid)

