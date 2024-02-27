import uuid

from typing import List
from unittest import TestCase

import faker

from ddt import data, ddt

from pyball.greenfield.meetup.domain.errors import InvalidPlayerCountError
from pyball.greenfield.meetup.domain.model.meetup import Meetup

fake: faker.Faker = faker.Faker()


@ddt
class TestMeetup(TestCase):
    def test_it_should_publish_an_event_when_a_player_is_added(self) -> None:
        # Arrange
        meetup_id = uuid.uuid4()
        player_id = uuid.uuid4()
        meetup = Meetup(id=meetup_id, date_time=fake.unique.date_time(), location=fake.word())

        # Act
        meetup.add_player(player_id)
        player_was_added_events: List[Meetup.PlayerWasAdded] = list(meetup.consume_events())

        # Assert
        self.assertEqual(len(player_was_added_events), 1)
        self.assertIsInstance(player_was_added_events[0], Meetup.PlayerWasAdded)
        self.assertEqual(player_was_added_events[0].player_id, player_id)
        self.assertEqual(player_was_added_events[0].meetup_id, meetup_id)

    @data(1, 11, 14, 37)
    def test_it_should_return_0_if_the_number_of_player_make_the_meetup_not_playable(
        self, player_count
    ) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        for _ in range(player_count):
            meetup.add_player(uuid.uuid4())

        # Assert
        with self.assertRaises(InvalidPlayerCountError):
            # Act
            meetup.create_teams()

    @data(10, 12)
    def test_it_should_create_2_team_when_player_count_is_10_or_12(self, player_count) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        for _ in range(player_count):
            meetup.add_player(uuid.uuid4())

        # Act
        meetup.create_teams()
        obtained_team_count = meetup.team_count
        team_were_created_event: Meetup.TeamsWereCreated = list(meetup.consume_events())[-1]

        # Assert
        self.assertIsInstance(team_were_created_event, Meetup.TeamsWereCreated)
        self.assertEqual(obtained_team_count, 2)
        self.assertEqual(len(team_were_created_event.teams), 2)

    @data(14, 16)
    def test_it_should_return_2_if_the_number_of_player_is_14_or_16(self, player_count) -> None:
        # Arrange
        meetup = Meetup(
            id=uuid.uuid4(),
            date_time=fake.unique.date_time(),
            location=fake.word(),
            possible_team_sizes=(7, 8),
        )
        for _ in range(player_count):
            meetup.add_player(uuid.uuid4())

        # Act
        meetup.create_teams()
        obtained_team_count = meetup.team_count
        team_were_created_event: Meetup.TeamsWereCreated = list(meetup.consume_events())[-1]

        # Assert
        self.assertIsInstance(team_were_created_event, Meetup.TeamsWereCreated)
        self.assertEqual(obtained_team_count, 2)
        self.assertEqual(len(team_were_created_event.teams), 2)

    def test_it_should_return_3_if_the_number_of_players_is_15(self) -> None:
        # Arrange
        player_count = 15
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        for _ in range(player_count):
            meetup.add_player(uuid.uuid4())

        # Act
        meetup.create_teams()
        obtained_team_count = meetup.team_count
        team_were_created_event: Meetup.TeamsWereCreated = list(meetup.consume_events())[-1]

        # Assert
        self.assertIsInstance(team_were_created_event, Meetup.TeamsWereCreated)
        self.assertEqual(obtained_team_count, 3)
        self.assertEqual(len(team_were_created_event.teams), 3)
        self.assertEqual(len(meetup.teams[0]), 5)
        self.assertEqual(len(meetup.teams[1]), 5)
        self.assertEqual(len(meetup.teams[2]), 5)

    def test_it_should_raise_an_error_if_the_player_count_is_not_playable(self) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        for _ in range(9):
            meetup.add_player(uuid.uuid4())

        # Assert
        with self.assertRaises(InvalidPlayerCountError):
            meetup.create_teams()

    def test_it_should_create_teams_with_different_players_in_each_team(self) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        for _ in range(10):
            meetup.add_player(uuid.uuid4())

        # Act
        meetup.create_teams()
        player_list_team_1 = set(meetup.teams[0])
        player_list_team_2 = set(meetup.teams[1])

        # Assert
        self.assertEqual(len(player_list_team_1.union(player_list_team_2)), 10)
