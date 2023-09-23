import datetime

from unittest import TestCase, mock

import faker
import peewee

from freezegun import freeze_time

from pyball import db
from pyball.callup.callup import CallUp
from pyball.callup.errors import CallUpMatchNotYetCreatedError
from pyball.callup.match import Match, PlayersStatInput
from pyball.callup.players import Players
from pyball.db.write_events.on_match_results_were_added import (
    update_all_seasons_player_table,
    update_current_season_player_table,
)
from pyball.db.write_events.on_player_was_created import (
    create_player_all_seasons_stats,
    create_player_current_season_stats,
)
from tests.utils import create_dict_player, create_dict_stats

fake: faker.Faker = faker.Faker()


class TestCallUpProcess(TestCase):
    @mock.patch("pyball.db.utils.backup_database")
    def test_call_up_as_yaml_adds_goals_when_results_are_set(self, _):
        # when
        for player in self._players[:10]:
            self._call_up.add_player(player=player["telegram_id"])

        obtained_yaml = self._call_up.as_yaml()

        # then
        self.assertIn("Naranja", obtained_yaml)
        self.assertIn("Verde", obtained_yaml)
        self.assertNotIn("goles", obtained_yaml)

        player_stat_input = PlayersStatInput()
        player_stat_input.add_stat(self._players[0]["name"])

        # when
        self._call_up.set_results(player_stat_input)
        obtained_yaml = self._call_up.as_yaml()

        # then
        self.assertIn("goles", obtained_yaml)

    def test_create_match_error_due_to_missing_players(self):
        # when
        for player in self._players[:5]:
            self._call_up.add_player(player=player["telegram_id"])

        # then
        with self.assertRaises(CallUpMatchNotYetCreatedError):
            _ = self._call_up.match

    def test_create_match_properly(self):
        # when
        for player in self._players[:10]:
            self._call_up.add_player(player=player["telegram_id"])

        # then
        self.assertIsNotNone(self._call_up.match)
        self.assertTrue(self._call_up.players.are_ready())

    @mock.patch("pyball.db.utils.backup_database")
    def test_set_match_results(self, _):
        # given
        players = Players.from_list(
            [
                self._players[0]["name"],
                self._players[1]["name"],
                self._players[2]["name"],
                self._players[3]["name"],
                self._players[4]["name"],
                self._players[5]["name"],
                self._players[6]["name"],
                self._players[7]["name"],
                self._players[8]["name"],
                self._players[9]["name"],
            ]
        )
        match = Match.from_dict(
            {
                "Verde": {
                    "jugadores": [
                        self._players[0]["name"],
                        self._players[1]["name"],
                        self._players[2]["name"],
                        self._players[3]["name"],
                        self._players[4]["name"],
                    ]
                },
                "Naranja": {
                    "jugadores": [
                        self._players[5]["name"],
                        self._players[6]["name"],
                        self._players[7]["name"],
                        self._players[8]["name"],
                        self._players[9]["name"],
                    ]
                },
            }
        )
        self._call_up = CallUp(
            date=self._date,
            main_chat_id=self._main_chat_id,
            main_chat_msg=self._main_chat_msg,
            location=self._location,
            players=players,
            match=match,
        )

        player_stat_input = PlayersStatInput()

        player_stat_input.add_stat(self._players[0]["name"], self._players[1]["name"])
        player_stat_input.add_stat(self._players[1]["name"], self._players[0]["name"])
        player_stat_input.add_stat(self._players[2]["name"], self._players[3]["name"])

        player_stat_input.add_stat(self._players[7]["name"], self._players[5]["name"])

        # when
        self._call_up.set_results(player_stat_input)

        # then
        match_info = db.utils.get_match(self._date)

        self.assertTrue(self._date in db.utils.get_matches_date_list(all_seasons=True))
        self.assertEqual(match_info["Verde"]["goles"], 3)
        self.assertEqual(match_info["Naranja"]["goles"], 1)

    def setUp(self):
        fake.unique.clear()
        # given
        self._date = fake.date_time()
        self._main_chat_id = fake.random_int()
        self._main_chat_msg = fake.random_int()
        self._location = fake.address()
        self._call_up = CallUp(
            date=self._date,
            main_chat_id=self._main_chat_id,
            main_chat_msg=self._main_chat_msg,
            location=self._location,
        )
        self._players = [
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
        ]

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables(
            [db.model.Player, db.model.MatchStatistic, db.model.CurrentSeason, db.model.AllSeasons]
        )
        for player in self._players:
            player_id = db.model.Player.insert(**player).execute()
            player["id"] = player_id

        self._all_statistics = [
            create_dict_stats(player=self._players[0]["id"], skill=6),
            create_dict_stats(player=self._players[1]["id"], skill=5),
            create_dict_stats(player=self._players[2]["id"], skill=4),
            create_dict_stats(player=self._players[3]["id"], skill=3),
            create_dict_stats(player=self._players[4]["id"], skill=2),
            create_dict_stats(player=self._players[5]["id"], skill=6),
            create_dict_stats(player=self._players[6]["id"], skill=5),
            create_dict_stats(player=self._players[7]["id"], skill=4),
            create_dict_stats(player=self._players[8]["id"], skill=3),
            create_dict_stats(player=self._players[9]["id"], skill=2),
            create_dict_stats(player=self._players[10]["id"], skill=6),
            create_dict_stats(player=self._players[11]["id"], skill=6),
        ]
        db.model.AllSeasons.insert_many(self._all_statistics).execute()

    def tearDown(self):
        db.model.database.close()


class TestCreatePlayerEvents(TestCase):
    def test_creating_player_creates_statistcs(self):
        self.assertFalse(list(db.model.Player.select().tuples()))
        self.assertFalse(list(db.model.CurrentSeason.select().tuples()))
        self.assertFalse(list(db.model.AllSeasons.select().tuples()))

        db.utils.create_player(fake.unique.name(), fake.unique.random_int(), fake.pybool())

        self.assertTrue(list(db.model.Player.select().tuples()))
        self.assertTrue(list(db.model.CurrentSeason.select().tuples()))
        self.assertTrue(list(db.model.AllSeasons.select().tuples()))

    def setUp(self):
        fake.unique.clear()
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables(
            [
                db.model.Player,
                db.model.MatchStatistic,
                db.model.CurrentSeason,
                db.model.AllSeasons,
            ]
        )

    def tearDown(self):
        db.model.database.close()


class TestCreatePlayersAndAddMatchResults(TestCase):
    @freeze_time(fake.date_time().replace(month=11, day=6))
    @mock.patch("pyball.db.utils.backup_database")
    def test_adding_first_results_update_stat_tables(self, _):
        # Create the players
        for player in self._players:
            db.utils.create_player(player["name"], player["telegram_id"], player["main"])
            player["id"] = db.model.Player.get(
                db.model.Player.telegram_id == player["telegram_id"]
            ).id

            player_current_season = db.utils.find_player(player["telegram_id"], all_seasons=False)
            player_all_seasons = db.utils.find_player(player["telegram_id"], all_seasons=True)

            self.assertEqual(player_current_season.goals, player_all_seasons.goals)
            self.assertEqual(player_current_season.assists, player_all_seasons.assists)
            self.assertEqual(player_current_season.wins, player_all_seasons.wins)
            self.assertEqual(player_current_season.losses, player_all_seasons.losses)
            self.assertEqual(player_current_season.ties, player_all_seasons.ties)

        # Add first match results

        team_a, team_b = fake.unique.safe_color_name(), fake.unique.safe_color_name()

        match_date = datetime.datetime.today().replace(hour=20, minute=0, second=0)
        match_statistics = [
            db.wrapper.MatchStatistic(match_date, self._players[0]["id"], team_a, 2, 1, "ties"),
            db.wrapper.MatchStatistic(match_date, self._players[1]["id"], team_a, 1, 1, "ties"),
            db.wrapper.MatchStatistic(match_date, self._players[2]["id"], team_b, 3, 0, "ties"),
            db.wrapper.MatchStatistic(match_date, self._players[3]["id"], team_b, 0, 2, "ties"),
        ]
        db.utils.add_match_results(match_statistics)

        player_2_current_season = db.utils.find_player(
            self._players[2]["telegram_id"], all_seasons=False
        )
        player_2_all_seasons = db.utils.find_player(
            self._players[2]["telegram_id"], all_seasons=True
        )

        self.assertEqual(player_2_current_season.goals, player_2_all_seasons.goals)
        self.assertEqual(player_2_current_season.goals, 3)
        self.assertEqual(player_2_current_season.assists, player_2_all_seasons.assists)
        self.assertEqual(player_2_current_season.assists, 0)
        self.assertEqual(player_2_current_season.wins, player_2_all_seasons.wins)
        self.assertEqual(player_2_current_season.wins, 0)
        self.assertEqual(player_2_current_season.losses, player_2_all_seasons.losses)
        self.assertEqual(player_2_current_season.losses, 0)
        self.assertEqual(player_2_current_season.ties, player_2_all_seasons.ties)
        self.assertEqual(player_2_current_season.ties, 1)

        # Add match results to the last season

        match_date = datetime.datetime.today().replace(month=6, hour=20, minute=0, second=0)
        match_statistics = [
            db.wrapper.MatchStatistic(match_date, self._players[0]["id"], team_a, 0, 0, "wins"),
            db.wrapper.MatchStatistic(match_date, self._players[1]["id"], team_a, 0, 0, "wins"),
            db.wrapper.MatchStatistic(match_date, self._players[2]["id"], team_b, 5, 1, "losses"),
            db.wrapper.MatchStatistic(match_date, self._players[3]["id"], team_b, 1, 3, "losses"),
        ]
        db.utils.add_match_results(match_statistics)

        player_2_current_season = db.utils.find_player(
            self._players[2]["telegram_id"], all_seasons=False
        )
        player_2_all_seasons = db.utils.find_player(
            self._players[2]["telegram_id"], all_seasons=True
        )

        self.assertNotEqual(player_2_current_season.goals, player_2_all_seasons.goals)
        self.assertNotEqual(player_2_current_season.assists, player_2_all_seasons.assists)
        self.assertEqual(player_2_current_season.wins, player_2_all_seasons.wins)
        self.assertNotEqual(player_2_current_season.losses, player_2_all_seasons.losses)
        self.assertEqual(player_2_current_season.ties, player_2_all_seasons.ties)

        self.assertEqual(player_2_current_season.goals, 3)
        self.assertEqual(player_2_all_seasons.goals, 8)

    def setUp(self):
        fake.unique.clear()
        self._players = [
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
        ]
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables(
            [
                db.model.Player,
                db.model.MatchStatistic,
                db.model.CurrentSeason,
                db.model.AllSeasons,
            ]
        )

    def tearDown(self):
        db.model.database.close()
