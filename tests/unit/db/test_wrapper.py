from unittest import TestCase, mock

import faker
import peewee

from pyball import db
from pyball.db.errors import (
    DbMatchesCountInconsistencyError,
    DbMatchStatisticsNotFoundError,
    DbMultiplePlayersFoundError,
    DbPlayerAlreadyExistentError,
    DbPlayerNotFoundError,
    DbScoreInconsistencyError,
    DbStatisticForPlayerInMatchAlreadyExistent,
    DbUnknownResultError,
)
from pyball.db.utils import (
    add_match_results,
    check_inconsistencies,
    create_player,
    find_player,
    fix_inconsistencies,
    get_match,
    get_matches_date_list,
    get_player_id_list,
    get_player_list,
    get_results_names,
    reid_player,
    rename_player,
    update_players_skill,
)

fake: faker.Faker = faker.Faker()


class TestPlayer(TestCase):
    def test_player_initialization_from_db(self):
        player_object = (
            db.model.Player.select().where(db.model.Player.telegram_id == self.player_id).get()
        )

        player_wrapped = db.wrapper.Player.from_db(player_object)

        self.assertEqual(player_wrapped.telegram_id, self.player_id)
        self.assertEqual(player_wrapped.name, self.player_name)
        self.assertEqual(str(player_wrapped), self.player_name)

    def test_compute_player_skill(self):
        wrapped_player = find_player(self.player_id)

        min_goals, max_goals = 0, 10
        min_assists, max_assists = 0, 5

        self.assertEqual(wrapped_player.skill, 0)

        wrapped_player.compute_skill(min_goals, max_goals, min_assists, max_assists)

        self.assertEqual(wrapped_player.skill, 44.75)

    def setUp(self):
        self.player_id = fake.unique.random_int()
        self.player_name = fake.unique.name()

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(
            [
                {
                    "telegram_id": self.player_id,
                    "name": self.player_name,
                    "main": True,
                    "goals": 5,
                    "assists": 1,
                    "wins": 1,
                    "losses": 0,
                    "ties": 1,
                    "rank": 8,
                }
            ]
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
        self.date = fake.unique.date_time()
        self.player_id = fake.unique.random_int()

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(
            [{"telegram_id": self.player_id, "name": fake.unique.date_time(), "main": True}]
        ).execute()
        db.model.MatchStatistic.insert_many(
            [
                {
                    "date": self.date,
                    "player": self.player_id,
                    "team": "Naranja",
                    "goals": 4,
                    "assists": 1,
                }
            ]
        ).execute()

    def tearDown(self):
        db.model.database.close()
