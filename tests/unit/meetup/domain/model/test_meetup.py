import uuid

from unittest import TestCase

import faker

from ddt import data, ddt

from pyball.greenfield.meetup.domain.model.meetup import Meetup

fake: faker.Faker = faker.Faker()


@ddt
class TestMeetup(TestCase):
    @data(1, 11, 14, 37)
    def test_it_should_return_0_if_the_number_of_player_make_the_meetup_not_playable(
        self, player_count
    ) -> None:
        # Arrange

        # Act
        obtained_team_count = Meetup.calculate_team_count(player_count)

        # Assert
        self.assertEqual(obtained_team_count, 0)

    @data(10, 12)
    def test_it_should_return_2_if_the_number_of_players_is_10_or_12(self, player_count) -> None:
        # Arrange

        # Act
        obtained_team_count = Meetup.calculate_team_count(player_count)

        # Assert
        self.assertEqual(obtained_team_count, 2)

    def test_it_should_return_3_if_the_number_of_players_is_15(self) -> None:
        # Arrange
        player_count = 15

        # Act
        obtained_team_count = Meetup.calculate_team_count(player_count)

        # Assert
        self.assertEqual(obtained_team_count, 3)

    def test_it_should_not_create_teams_if_the_player_count_is_not_playable(self) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())

        # Act
        for _ in range(9):
            meetup.add_player(uuid.uuid4())

        # Assert
        self.assertIsNone(meetup.teams)

    @data(10, 12)
    def test_it_should_create_2_teams_when_player_count(self, player_count) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())
        expected_player_count_in_each_team = player_count / 2

        # Act
        for _ in range(player_count):
            meetup.add_player(uuid.uuid4())

        # Assert
        self.assertIsNotNone(meetup.teams)
        self.assertEqual(len(meetup.teams), 2)
        self.assertEqual(len(meetup.teams[0]), expected_player_count_in_each_team)
        self.assertEqual(len(meetup.teams[1]), expected_player_count_in_each_team)

    def test_it_should_create_teams_with_different_players_in_each_team(self) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())

        # Act
        for _ in range(10):
            meetup.add_player(uuid.uuid4())
        player_list_team_1 = set(meetup.teams[0])
        player_list_team_2 = set(meetup.teams[1])

        # Assert
        self.assertEqual(len(player_list_team_1.union(player_list_team_2)), 10)

    def test_it_should_create_3_teams_when_player_count_is_15(self) -> None:
        # Arrange
        meetup = Meetup(id=uuid.uuid4(), date_time=fake.unique.date_time(), location=fake.word())

        # Act
        for _ in range(15):
            meetup.add_player(uuid.uuid4())

        # Assert
        self.assertEqual(len(meetup.players), 15)
        self.assertIsNotNone(meetup.teams)
        self.assertEqual(len(meetup.teams), 3)
        self.assertEqual(len(meetup.teams[0]), 5)
        self.assertEqual(len(meetup.teams[1]), 5)
        self.assertEqual(len(meetup.teams[2]), 5)

    def test_it_should_remove_teams_if_the_player_count_is_not_playable(self) -> None:
        # Arrange

        # Act

        # Assert
        pass
