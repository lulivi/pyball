import random

from pathlib import Path
from string import Template
from unittest import TestCase, mock

import faker

from pyball import db
from pyball.callup.match import Match, PlayersStatInput, Team
from tests.utils import create_wrapped_player

fake: faker.Faker = faker.Faker()
TEMPLATE_DIR = Path(__file__).resolve().parents[2].joinpath("data")


class TestPlayersStatInput(TestCase):
    @mock.patch("pyball.callup.match.find_player")
    def test_players_stat_input_add_goal(self, mock_find_player):
        scorer = create_wrapped_player()
        assistant = create_wrapped_player()
        expected_dict = {
            scorer.name: {
                "goals": 1,
                "assists": 0,
            },
            assistant.name: {
                "goals": 0,
                "assists": 1,
            },
        }
        mock_find_player.side_effect = [scorer, assistant]
        players_stat_input = PlayersStatInput()

        players_stat_input.add_stat(scorer.name, assistant.name)

        self.assertDictEqual(players_stat_input.result, expected_dict)

    @mock.patch("pyball.callup.match.find_player")
    def test_players_stat_input_len(self, mock_find_player):
        scorer = create_wrapped_player()
        assistant = create_wrapped_player()
        mock_find_player.side_effect = [scorer, assistant]
        players_stat_input = PlayersStatInput()

        players_stat_input.add_stat(scorer.name, assistant.name)

        self.assertEqual(len(players_stat_input), 2)


class TestTeam(TestCase):
    def test_team_player_addition(self):
        player = create_wrapped_player()

        team = Team()

        team.append(player)

        self.assertEqual(team.players, [player])
        self.assertEqual(team[0], player)

    def test_team_player_swapping(self):
        players = []
        for _ in range(5):
            players.append(create_wrapped_player())

        other_player = create_wrapped_player()

        team = Team(players)

        self.assertNotIn(other_player, team)

        team[3] = other_player

        self.assertIn(other_player, team)

    def test_team_as_yaml(self):
        players = []
        for _ in range(5):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)
        score = fake.random_int()
        team_name = random.choice(Match.team_names)

        expected_output = Template(
            TEMPLATE_DIR.joinpath("team_as_yaml.template").read_text()
        ).substitute(
            team_name=team_name,
            score=score,
            player_0=players[0].name,
            player_1=players[1].name,
            player_2=players[2].name,
            player_3=players[3].name,
            player_4=players[4].name,
        )

        team = Team(players=players, score=score)

        self.assertEqual(team.as_yaml(team_name), expected_output)

    def test_team_as_yaml_no_goals(self):
        players = []
        for _ in range(5):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)
        team_name = random.choice(Match.team_names)

        expected_output = Template(
            TEMPLATE_DIR.joinpath("team_as_yaml-no_goals.template").read_text()
        ).substitute(
            team_name=team_name,
            player_0=players[0].name,
            player_1=players[1].name,
            player_2=players[2].name,
            player_3=players[3].name,
            player_4=players[4].name,
        )

        team = Team(players=players)

        self.assertEqual(team.as_yaml(team_name), expected_output)

    def test_team_repr(self):
        players = []
        for _ in range(5):
            players.append(create_wrapped_player())
        players.sort(key=lambda player: player.name)

        player_str = ", ".join(list(map(lambda player: player.name, players)))
        expected_output = f"Team({player_str})"

        team = Team(players=players)

        self.assertEqual(repr(team), expected_output)


class TestMatch(TestCase):
    def test_create_automatic_match(self):
        pass

    def test_create_manual_match(self):
        pass

    def test_swap_players(self):
        pass

    def test_set_results(self):
        pass

    def test_as_yaml(self):
        pass

    def test_from_dict(self):
        pass
