import uuid

from unittest import TestCase

import faker

from pyball.greenfield.meetup.application.create_meetup import CreateMeetup
from pyball.greenfield.meetup.application.errors import MeetupDateNotFound, MeetupIdNotFound
from pyball.greenfield.meetup.application.get_meetup import GetMeetup
from tests.unit.meetup.application.fake_meetup_repository import FakeMeetupRepository

fake: faker.Faker = faker.Faker()


class TestGetMeetup(TestCase):
    def test_it_should_return_a_meetup_by_id(self) -> None:
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_date_time = fake.unique.date_time()
        fake_location = fake.unique.user_name()
        fake_meetup_respository = FakeMeetupRepository()
        CreateMeetup(fake_meetup_respository).create(
            id=fake_uuid,
            date_time=fake_date_time,
            location=fake_location,
        )

        # Act
        obtained_meetup = GetMeetup(fake_meetup_respository).by_id(id=fake_uuid)

        # Assert
        self.assertEqual(obtained_meetup.id, fake_uuid)
        self.assertEqual(obtained_meetup.date_time, fake_date_time)
        self.assertEqual(obtained_meetup.location, fake_location)

    def test_it_should_raise_an_exception_when_meetup_is_not_found_by_id(self):
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_meetup_respository = FakeMeetupRepository()

        # Assert
        with self.assertRaises(MeetupIdNotFound) as cm:
            # Act
            GetMeetup(fake_meetup_respository).by_id(fake_uuid)

        self.assertEqual(cm.exception.id, fake_uuid)

    def test_it_should_return_a_meetup_by_date(self) -> None:
        # Arrange
        fake_uuid = uuid.uuid4()
        fake_date_time = fake.unique.date_time()
        fake_location = fake.unique.user_name()
        fake_meetup_respository = FakeMeetupRepository()
        CreateMeetup(fake_meetup_respository).create(
            id=fake_uuid,
            date_time=fake_date_time,
            location=fake_location,
        )

        # Act
        obtained_meetup = GetMeetup(fake_meetup_respository).by_date(fake_date_time)

        # Assert
        self.assertEqual(obtained_meetup.id, fake_uuid)
        self.assertEqual(obtained_meetup.date_time, fake_date_time)
        self.assertEqual(obtained_meetup.location, fake_location)

    def test_it_should_raise_an_exception_when_meetup_is_not_found_by_date(self) -> None:
        # Arrange
        fake_date_time = fake.unique.date_time()
        fake_meetup_respository = FakeMeetupRepository()

        # Assert
        with self.assertRaises(MeetupDateNotFound) as cm:
            # Act
            GetMeetup(fake_meetup_respository).by_date(fake_date_time)

        self.assertEqual(cm.exception.date_time, fake_date_time)
