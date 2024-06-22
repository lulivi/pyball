import uuid

from unittest import TestCase

import faker

from tests.unit.meetup.application.fake_meetup_repository import FakeMeetupRepository

from pyball.greenfield.meetup.application.create_meetup import CreateMeetup
from pyball.greenfield.meetup.domain.errors import MeetupDateAlreadyUsed, MeetupIdAlreadyUsed

fake: faker.Faker = faker.Faker()


class TestCreateMeetup(TestCase):
    def test_meetup_is_created(self) -> None:
        # Arrange
        fake_meetup_respository = FakeMeetupRepository()
        fake_uuid = uuid.uuid4()
        fake_date_time = fake.unique.date_time()
        fake_location = fake.unique.user_name()

        # Act
        CreateMeetup(fake_meetup_respository).create(
            id=fake_uuid, date_time=fake_date_time, location=fake_location
        )

        # Assert
        obtained_meetup = fake_meetup_respository.get(fake_uuid)
        self.assertIsNotNone(obtained_meetup)
        self.assertEqual(fake_uuid, obtained_meetup.id)
        self.assertEqual(fake_date_time, obtained_meetup.date_time)
        self.assertEqual(fake_location, obtained_meetup.location)

    def test_exception_is_raised_when_meetup_already_exists(self) -> None:
        # Arrange
        create_meetup = CreateMeetup(FakeMeetupRepository())
        fake_uuid = uuid.uuid4()
        create_meetup.create(
            id=fake_uuid, date_time=fake.unique.date_time(), location=fake.unique.user_name()
        )

        # Assert
        with self.assertRaises(MeetupIdAlreadyUsed) as cm:
            # Act
            create_meetup.create(
                id=fake_uuid, date_time=fake.unique.date_time(), location=fake.unique.user_name()
            )

        self.assertEqual(cm.exception.id, fake_uuid)

    def test_exception_is_raised_when_meetup_date_already_in_use(self) -> None:
        # Arrange
        create_meetup = CreateMeetup(FakeMeetupRepository())
        fake_date_time = fake.unique.date_time()
        create_meetup.create(
            id=uuid.uuid4(), date_time=fake_date_time, location=fake.unique.user_name()
        )

        # Assert
        with self.assertRaises(MeetupDateAlreadyUsed) as cm:
            # Act
            create_meetup.create(
                id=uuid.uuid4(), date_time=fake_date_time, location=fake.unique.user_name()
            )

        self.assertEqual(cm.exception.date_time, fake_date_time)
