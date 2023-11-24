import datetime
import uuid

from typing import Optional
from unittest import TestCase

import faker

from pyball.match.application.create_match import CreateMatch
from pyball.match.domain.errors import DateAlreadyUsedError, MatchAlreadyExistentError
from pyball.match.domain.matches import Matches
from pyball.match.domain.model.match import Match

fake: faker.Faker = faker.Faker()


class FakeMatchRepository(Matches):
    def __init__(self) -> None:
        self.matches = {}

    def save(self, match: Match) -> None:
        self.matches[match.id] = match

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self.matches.get(id)

    def get_by_date(self, date: datetime.datetime) -> Optional[Match]:
        for match in self.matches.values():
            if match.date == date:
                return match

        return None



class TestCreateMatch(TestCase):
    def test_match_is_created(self) -> None:
        # Arrange
        fake_match_respository = FakeMatchRepository()
        create_match = CreateMatch(fake_match_respository)
        fake_uuid = uuid.uuid4()
        fake_date = fake.unique.date_time()
        fake_location = fake.unique.user_name()

        # Act
        create_match.create(id=fake_uuid, date=fake_date, location=fake_location)

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
