import datetime

from unittest import TestCase

import faker
import peewee

from freezegun import freeze_time

from pyball import db
from pyball.db.write_events.on_match_results_were_added import (
    update_all_seasons_player_table,
    update_current_season_player_table,
)
from tests.utils import create_dict_player, create_dict_stats

fake: faker.Faker = faker.Faker()


class TestUpdatePlayerSeasonStats(TestCase):
    @freeze_time(fake.date_time().replace(day=16, month=12))
    def test_player_current_season_stats_are_properly_updated(self):
        update_current_season_player_table(
            self._dates[1],
            {
                self._players[4]["id"]: "losses",
                self._players[1]["id"]: "losses",
                self._players[3]["id"]: "wins",
                self._players[2]["id"]: "wins",
            },
        )

        expected_player_one_stats = {
            "goals": 2,
            "assists": 0,
            "wins": 0,
            "ties": 0,
            "losses": 1,
        }
        obtained_stats = (
            db.model.CurrentSeason.select()
            .where(db.model.CurrentSeason.player == self._players[4]["id"])
            .dicts()
            .get()
        )
        self.assertEqual(expected_player_one_stats["goals"], obtained_stats["goals"])
        self.assertEqual(expected_player_one_stats["assists"], obtained_stats["assists"])
        self.assertEqual(expected_player_one_stats["wins"], obtained_stats["wins"])
        self.assertEqual(expected_player_one_stats["ties"], obtained_stats["ties"])
        self.assertEqual(expected_player_one_stats["losses"], obtained_stats["losses"])

    @freeze_time(fake.date_time().replace(day=16, month=12))
    def test_player_all_seasons_stats_are_properly_updated(self):
        update_all_seasons_player_table(
            self._dates[1],
            {
                self._players[4]["id"]: "losses",
                self._players[1]["id"]: "losses",
                self._players[3]["id"]: "wins",
                self._players[2]["id"]: "wins",
            },
        )
        update_all_seasons_player_table(
            self._dates[0],
            {
                self._players[0]["id"]: "losses",
                self._players[1]["id"]: "losses",
                self._players[2]["id"]: "wins",
                self._players[3]["id"]: "wins",
            },
        )
        expected_player_three_stats = {
            "goals": 4,
            "assists": 0,
            "wins": 2,
            "ties": 0,
            "losses": 0,
        }
        obtained_stats = (
            db.model.AllSeasons.select()
            .where(db.model.AllSeasons.player == self._players[3]["id"])
            .dicts()
            .get()
        )
        self.assertEqual(expected_player_three_stats["goals"], obtained_stats["goals"])
        self.assertEqual(expected_player_three_stats["assists"], obtained_stats["assists"])
        self.assertEqual(expected_player_three_stats["wins"], obtained_stats["wins"])
        self.assertEqual(expected_player_three_stats["ties"], obtained_stats["ties"])
        self.assertEqual(expected_player_three_stats["losses"], obtained_stats["losses"])

    def setUp(self):
        fake.unique.clear()
        self._players = [
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
        ]
        faker_date = datetime.datetime.now()
        self._dates = [
            fake.unique.date_time_between_dates(
                datetime_start=faker_date.replace(day=5, month=1),
                datetime_end=faker_date.replace(day=17, month=7),
            ),
            fake.unique.date_time_between_dates(
                datetime_start=faker_date.replace(day=13, month=9),
                datetime_end=faker_date.replace(day=8, month=12),
            ),
        ]
        self._match_statistics = [
            {
                "date": self._dates[0],
                "player": self._players[0]["id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": self._dates[0],
                "player": self._players[1]["id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 1,
            },
            {
                "date": self._dates[0],
                "player": self._players[2]["id"],
                "team": "Verde",
                "goals": 4,
                "assists": 0,
            },
            {
                "date": self._dates[0],
                "player": self._players[3]["id"],
                "team": "Verde",
                "goals": 1,
                "assists": 0,
            },
            # Second match
            {
                "date": self._dates[1],
                "player": self._players[4]["id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[1]["id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 1,
            },
            {
                "date": self._dates[1],
                "player": self._players[3]["id"],
                "team": "Verde",
                "goals": 3,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[2]["id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
        ]
        self._current_season_stats = [
            create_dict_stats(
                self._players[player_index]["id"],
                goals=0,
                assists=0,
                wins=0,
                losses=0,
                ties=0,
                skill=0,
            )
            for player_index in range(len(self._players))
        ]
        self._all_season_stats = [
            create_dict_stats(
                self._players[player_index]["id"],
                goals=0,
                assists=0,
                wins=0,
                losses=0,
                ties=0,
                skill=0,
            )
            for player_index in range(len(self._players))
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
        db.model.Player.insert_many(self._players).execute()
        db.model.MatchStatistic.insert_many(self._match_statistics).execute()
        db.model.CurrentSeason.insert_many(self._current_season_stats).execute()
        db.model.AllSeasons.insert_many(self._all_season_stats).execute()

    def tearDown(self):
        db.model.database.close()
