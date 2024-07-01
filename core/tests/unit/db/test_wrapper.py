from unittest import TestCase

import faker
import peewee

from pyball.legacy import db
from pyball.legacy.db.errors import DbUnknownResultError
from pyball.legacy.db.utils import find_player

fake: faker.Faker = faker.Faker()


class TestPlayer(TestCase):
    def test_player_initialization_from_db(self):
        player_wrapped = db.wrapper.Player.from_db(
            db.model.Player.get(db.model.Player.id == self.player_id),
            db.model.AllSeasons.get(db.model.AllSeasons.player == self.player_id),
        )

        self.assertEqual(player_wrapped.telegram_id, self.player_telegram_id)
        self.assertEqual(player_wrapped.name, self.player_name)
        self.assertEqual(str(player_wrapped), self.player_name)

    def test_compute_player_skill(self):
        wrapped_player = find_player(self.player_telegram_id, all_seasons=True)

        min_goals, max_goals = 0, 10
        min_assists, max_assists = 0, 5

        self.assertEqual(wrapped_player.skill, 0)

        wrapped_player.compute_skill(min_goals, max_goals, min_assists, max_assists)

        self.assertEqual(wrapped_player.skill, 44.75)

    def setUp(self):
        fake.unique.clear()
        self.player_telegram_id = fake.unique.random_int()
        self.player_name = fake.unique.name()

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables(
            [
                db.model.Player,
                db.model.MatchStatistic,
                db.model.AllSeasons,
                db.model.CurrentSeason,
            ]
        )
        self.player_id = db.model.Player.insert(
            {
                "telegram_id": self.player_telegram_id,
                "name": self.player_name,
                "main": True,
                "rank": 8,
            }
        ).execute()
        db.model.AllSeasons.insert(
            {
                "player": self.player_id,
                "goals": 5,
                "assists": 1,
                "wins": 1,
                "losses": 0,
                "ties": 1,
            }
        ).execute()

    def tearDown(self):
        db.model.database.close()


class TestMatchStatistic(TestCase):
    def test_set_result(self):
        match_statistic_object = (
            db.model.MatchStatistic.select()
            .where(
                db.model.MatchStatistic.date == self.date,
                db.model.MatchStatistic.player == self.player_id,
            )
            .get()
        )

        match_statistic_wrapped = db.wrapper.MatchStatistic(
            date=match_statistic_object.date,
            player=match_statistic_object.player,
            team=match_statistic_object.team,
            goals=match_statistic_object.goals,
            assists=match_statistic_object.assists,
        )
        self.assertIsNone(match_statistic_wrapped.result)

        match_statistic_wrapped.set_result("wins")

        self.assertEqual(match_statistic_wrapped.result, "wins")

    def test_set_result_error(self):
        match_statistic_object = (
            db.model.MatchStatistic.select()
            .where(
                db.model.MatchStatistic.date == self.date,
                db.model.MatchStatistic.player == self.player_id,
            )
            .get()
        )

        match_statistic_wrapped = db.wrapper.MatchStatistic(
            date=match_statistic_object.date,
            player=match_statistic_object.player,
            team=match_statistic_object.team,
            goals=match_statistic_object.goals,
            assists=match_statistic_object.assists,
        )
        self.assertIsNone(match_statistic_wrapped.result)

        with self.assertRaises(DbUnknownResultError):
            match_statistic_wrapped.set_result("Won")

    def setUp(self):
        fake.unique.clear()
        self.date = fake.unique.date_time()
        self.player_telegram_id = fake.unique.random_int()

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        self.player_id = db.model.Player.insert(
            {"telegram_id": self.player_telegram_id, "name": fake.unique.date_time(), "main": True}
        ).execute()
        db.model.MatchStatistic.insert(
            {
                "date": self.date,
                "player": self.player_id,
                "team": "Naranja",
                "goals": 4,
                "assists": 1,
            }
        ).execute()

    def tearDown(self):
        db.model.database.close()
