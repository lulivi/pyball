from unittest import TestCase

import faker
import peewee

from pyball.legacy import db
from pyball.legacy.db.errors import DbPlayerStatsAlreadyExistentError
from pyball.legacy.db.write_events.on_player_was_created import (
    create_player_all_seasons_stats,
    create_player_current_season_stats,
)
from tests.utils import create_dict_player

fake: faker.Faker = faker.Faker()


class TestCreatePlayerCurrentSeasonStats(TestCase):
    def test_create_player_current_season(self):
        create_player_current_season_stats(self._player["id"])

        obtained_player = db.model.CurrentSeason.get(self._player["id"])

        self.assertEqual(obtained_player.goals, 0)
        self.assertEqual(obtained_player.assists, 0)
        self.assertEqual(obtained_player.wins, 0)
        self.assertEqual(obtained_player.ties, 0)
        self.assertEqual(obtained_player.losses, 0)

    def test_create_player_current_season_is_already_created(self):
        create_player_current_season_stats(self._player["id"])

        with self.assertRaises(DbPlayerStatsAlreadyExistentError) as cm:
            create_player_current_season_stats(self._player["id"])

        self.assertEqual(cm.exception.name, self._player["name"])
        self.assertEqual(cm.exception.table, "CurrentSeason")

    def setUp(self):
        fake.unique.clear()
        self._player = create_dict_player()

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
        db.model.Player.insert(**self._player).execute()

    def tearDown(self):
        db.model.database.close()


class TestCreatePlayerAllSeasonsStats(TestCase):
    def test_create_player_all_season(self):
        create_player_all_seasons_stats(self._player["id"])

        obtained_player = db.model.AllSeasons.get(self._player["id"])

        self.assertEqual(obtained_player.goals, 0)
        self.assertEqual(obtained_player.assists, 0)
        self.assertEqual(obtained_player.wins, 0)
        self.assertEqual(obtained_player.ties, 0)
        self.assertEqual(obtained_player.losses, 0)

    def test_create_player_all_seasons_is_already_created(self):
        create_player_all_seasons_stats(self._player["id"])

        with self.assertRaises(DbPlayerStatsAlreadyExistentError) as cm:
            create_player_all_seasons_stats(self._player["id"])

        self.assertEqual(cm.exception.name, self._player["name"])
        self.assertEqual(cm.exception.table, "AllSeasons")

    def setUp(self):
        fake.unique.clear()
        self._player = create_dict_player()

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
        db.model.Player.insert(self._player).execute()

    def tearDown(self):
        db.model.database.close()
