import random

from pathlib import Path
from string import Template
from unittest import TestCase, mock

import faker

from pyball.legacy import db
from pyball.legacy.callup.errors import (
    CallUpMultiplePlayersFoundError,
    CallUpPlayerAlreadyCalledUpError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayerNotCalledUpError,
)
from pyball.legacy.callup.players import Players, find_player
from pyball.legacy.db.errors import DbMultiplePlayersFoundError, DbPlayerNotFoundError
from tests.utils import create_wrapped_player

fake: faker.Faker = faker.Faker()
TEMPLATE_DIR = Path(__file__).resolve().parents[2].joinpath("data")


class TestPlayers(TestCase):
    def test_maximum_auto_calculated_less_than_ten(self):
        players = []
        for _ in range(8):
            players.append(create_wrapped_player())

        players_object = Players(players=players)

        self.assertFalse(players_object.are_ready())
        self.assertEqual(players_object.maximum, 10)

    def test_maximum_auto_calculated_equal_to_ten(self):
        players = []
        for _ in range(10):
            players.append(create_wrapped_player())

        players_object = Players(players=players)

        self.assertTrue(players_object.are_ready())
        self.assertEqual(players_object.maximum, 10)

    def test_maximum_fixed(self):
        players = []
        maximum = 14
        for _ in range(10):
            players.append(create_wrapped_player())

        players_object = Players(maximum=maximum, players=players)

        self.assertFalse(players_object.are_ready())
        self.assertEqual(players_object.maximum, maximum)

    def test_maximum_fix(self):
        players = []
        for _ in range(10):
            players.append(create_wrapped_player())

        players_object = Players(players=players)

        self.assertTrue(players_object.are_ready())
        self.assertEqual(players_object.maximum, 10)

        players_object.set_maximum(14)

        self.assertFalse(players_object.are_ready())
        self.assertEqual(players_object.maximum, 14)

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_player_join(self, mock_find_player):
        players_object = Players()

        players_object.join(fake.unique.name())

        self.assertEqual(len(players_object), 1)
        mock_find_player.assert_called_once()

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_player_join_already_called_up(self, mock_find_player):
        player_a = create_wrapped_player()
        mock_find_player.return_value = player_a
        players_object = Players(players=[player_a])

        with self.assertRaises(CallUpPlayerAlreadyCalledUpError):
            players_object.join(player_a)

        mock_find_player.assert_called_once()

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_player_join_when_aready_ready_should_set_automatic_maximum(self, _):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()
        player_c = create_wrapped_player()

        players_object = Players(maximum=2, players=[player_a, player_b])

        self.assertTrue(players_object.are_ready())
        self.assertEqual(players_object.maximum, 2)

        players_object.join(player_c.name)

        self.assertFalse(players_object.are_ready())
        self.assertEqual(players_object.maximum, 10)

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_player_leave(self, mock_find_player):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()
        mock_find_player.return_value = player_b

        players_object = Players(players=[player_a, player_b])

        players_object.leave(player_b)

        self.assertEqual(len(players_object), 1)
        self.assertEqual(players_object.players[0], player_a)
        mock_find_player.assert_called_once()

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_player_leave_not_called_up(self, mock_find_player):
        player_a = create_wrapped_player()
        mock_find_player.return_value = player_a
        players_object = Players()

        with self.assertRaises(CallUpPlayerNotCalledUpError):
            players_object.leave(player_a)

        mock_find_player.assert_called_once()

    def test_remaining_players_when_eight_are_missing(self):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()

        players_object = Players(maximum=10, players=[player_a, player_b])

        self.assertEqual(players_object.remaining(), 10 - len(players_object))

    def test_remaining_players_when_no_players_are_missing(self):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()

        players_object = Players(maximum=2, players=[player_a, player_b])

        self.assertEqual(players_object.remaining(), 0)

    def test_are_ready_when_there_are_missing_players(self):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()

        players_object = Players(maximum=4, players=[player_a, player_b])

        self.assertFalse(players_object.are_ready())

    def test_are_ready_when_there_are_no_missing_players(self):
        player_a = create_wrapped_player()
        player_b = create_wrapped_player()

        players_object = Players(maximum=2, players=[player_a, player_b])

        self.assertTrue(players_object.are_ready())

    def test_as_yaml(self):
        players = []
        for _ in range(10):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)
        expected_output = Template(
            TEMPLATE_DIR.joinpath("players_as_yaml.template").read_text()
        ).substitute(
            player_0=players[0],
            player_1=players[1],
            player_2=players[2],
            player_3=players[3],
            player_4=players[4],
            player_5=players[5],
            player_6=players[6],
            player_7=players[7],
            player_8=players[8],
            player_9=players[9],
        )

        players_object = Players(players=players)

        self.assertEqual(expected_output, players_object.to_yaml())

    def test_str_should_return_a_yaml(self):
        players = []
        for _ in range(10):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)
        expected_output = Template(
            TEMPLATE_DIR.joinpath("players_as_yaml.template").read_text()
        ).substitute(
            player_0=players[0],
            player_1=players[1],
            player_2=players[2],
            player_3=players[3],
            player_4=players[4],
            player_5=players[5],
            player_6=players[6],
            player_7=players[7],
            player_8=players[8],
            player_9=players[9],
        )

        players_object = Players(players=players)

        self.assertEqual(expected_output, str(players_object))

    def test_as_yaml_when_there_are_missing_players(self):
        players = []
        for _ in range(8):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)
        expected_output = Template(
            TEMPLATE_DIR.joinpath("players_as_yaml.template").read_text()
        ).substitute(
            player_0=players[0],
            player_1=players[1],
            player_2=players[2],
            player_3=players[3],
            player_4=players[4],
            player_5=players[5],
            player_6=players[6],
            player_7=players[7],
            player_8="?????",
            player_9="?????",
        )

        players_object = Players(players=players)

        self.assertEqual(expected_output, players_object.to_yaml())

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_from_list(self, mock_find_player):
        players = []
        for _ in range(10):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)

        mock_find_player.side_effect = players

        player_names = list(map(lambda player: player.name, players))
        random.shuffle(player_names)

        players_object = Players.from_list(player_names)

        self.assertEqual(players, players_object.players)
        self.assertTrue(players_object.are_ready())

    @mock.patch("pyball.legacy.callup.players.find_player")
    def test_from_list_when_there_are_missing_players(self, mock_find_player):
        players = []
        for _ in range(8):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)

        mock_find_player.side_effect = players

        player_names = list(map(lambda player: player.name, players))
        random.shuffle(player_names)

        players_object = Players.from_list([*player_names, "?????", "?????"])

        self.assertEqual(players, players_object.players)
        self.assertFalse(players_object.are_ready())
        self.assertEqual(players_object.remaining(), 2)


class TestFindPlayer(TestCase):
    @mock.patch("pyball.legacy.callup.players.db.utils.find_player")
    def test_find_player_when_exists(self, mock_find_player):
        expected_player = create_wrapped_player()
        mock_find_player.return_value = expected_player

        obtained_player = find_player("test")

        self.assertEqual(obtained_player, expected_player)

    @mock.patch("pyball.legacy.callup.players.db.utils.find_player")
    def test_find_player_when_the_player_does_not_exist(self, mock_find_player):
        mock_find_player.side_effect = DbPlayerNotFoundError("p")

        with self.assertRaises(CallUpPlayerDoesNotExistError):
            _ = find_player("test")

        mock_find_player.assert_called_once()

    @mock.patch("pyball.legacy.callup.players.db.utils.find_player")
    def test_find_player_when_player_name_returns_multiple_possible(self, mock_find_player):
        mock_find_player.side_effect = DbMultiplePlayersFoundError(["p1", "p2"], "p")

        with self.assertRaises(CallUpMultiplePlayersFoundError):
            _ = find_player("test")

        mock_find_player.assert_called_once()
