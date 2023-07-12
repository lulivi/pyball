from pathlib import Path
from unittest import TestCase, mock

import faker
import peewee

from pyball import db
from pyball.callup.callup import CallUp
from pyball.callup.errors import CallUpMatchNotYetCreatedError
from pyball.callup.match import Match, PlayersStatInput
from pyball.callup.players import Players

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

        self.assertTrue(self._date in db.utils.get_matches_date_list())
        self.assertEqual(match_info["Verde"]["goles"], 3)
        self.assertEqual(match_info["Naranja"]["goles"], 1)

    def setUp(self):
        # given
        fake.unique.clear()
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
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 6,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 5,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 4,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 3,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 2,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 6,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 5,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 4,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 3,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 2,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 6,
            },
            {
                "telegram_id": fake.unique.random_int(),
                "name": fake.unique.name(),
                "main": True,
                "skill": 6,
            },
        ]
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(
            self._players,
            fields=[db.model.Player.telegram_id, db.model.Player.name, db.model.Player.main],
        ).execute()

    def tearDown(self):
        db.model.database.close()
