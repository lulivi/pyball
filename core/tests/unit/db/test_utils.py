import datetime

from typing import List
from unittest import TestCase, mock, skip

import faker
import peewee

from freezegun import freeze_time
from tests.utils import create_dict_player, create_dict_stats

from pyball.legacy import db
from pyball.legacy.db.errors import (
    DbMatchesCountInconsistencyError,
    DbMatchStatisticsNotFoundError,
    DbMultiplePlayersFoundError,
    DbPlayerAlreadyExistentError,
    DbPlayerNotFoundError,
    DbPlayerStatisticsNotFoundError,
    DbScoreInconsistencyError,
    DbStatisticForPlayerInMatchAlreadyExistent,
)
from pyball.legacy.db.utils import (
    add_match_results,
    check_inconsistencies,
    create_player,
    find_player,
    fix_inconsistencies,
    get_last_end_of_august,
    get_match,
    get_matches_date_list,
    get_player_id_list,
    get_player_list,
    get_results_names,
    reid_player,
    rename_player,
)

fake: faker.Faker = faker.Faker()


class TestGetResultsNames(TestCase):
    def test_get_win_for_team_0(self):
        expected_results = ("wins", "losses")
        results = get_results_names(1, 0)

        self.assertTupleEqual(results, expected_results)

    def test_get_win_for_team_1(self):
        expected_results = ("losses", "wins")
        results = get_results_names(0, 123123)

        self.assertTupleEqual(results, expected_results)

    def test_get_tie(self):
        expected_results = ("ties", "ties")
        results = get_results_names(0, 0)

        self.assertTupleEqual(results, expected_results)


class TestGetLastEndOfAugust(TestCase):
    @freeze_time(fake.date_time().replace(day=25, month=9))
    def test_get_last_end_of_august_on_september(self):
        current_fake_date = datetime.datetime.today()

        expected_august = current_fake_date.replace(month=8, day=31)
        obtained_august = get_last_end_of_august()

        self.assertEqual(expected_august.year, obtained_august.year)
        self.assertEqual(expected_august.month, obtained_august.month)
        self.assertEqual(expected_august.day, obtained_august.day)

    @freeze_time(fake.date_time().replace(day=6, month=5))
    def test_get_last_end_of_august_on_may(self):
        current_fake_date = datetime.datetime.today()

        expected_august = current_fake_date.replace(
            year=current_fake_date.year - 1, month=8, day=31
        )
        obtained_august = get_last_end_of_august()

        self.assertEqual(expected_august.year, obtained_august.year)
        self.assertEqual(expected_august.month, obtained_august.month)
        self.assertEqual(expected_august.day, obtained_august.day)


class TestFindPlayer(TestCase):
    def test_find_player_by_id(self):
        expected_player_telegram_id = self._first_player["telegram_id"]
        expected_player_name = self._first_player["name"]
        player = find_player(self._first_player["telegram_id"])

        self.assertEqual(player.telegram_id, expected_player_telegram_id)
        self.assertEqual(player.name, expected_player_name)

    def test_find_player_by_name(self):
        expected_player_telegram_id = self._first_player["telegram_id"]
        expected_player_name = self._first_player["name"]
        player = find_player(self._first_player["name"])

        self.assertEqual(player.telegram_id, expected_player_telegram_id)
        self.assertEqual(player.name, expected_player_name)

    def test_find_player_when_name_not_existent(self):
        with self.assertRaises(DbPlayerNotFoundError):
            _ = find_player(fake.unique.name())

    def test_find_player_when_id_not_existent(self):
        with self.assertRaises(DbPlayerNotFoundError):
            _ = find_player(fake.unique.random_int())

    def test_find_player_when_multiple_found(self):
        with self.assertRaises(DbMultiplePlayersFoundError):
            # Since the name of the third player is composed by the name of the second player,
            # if only one word of the name is provided, it will find the two players.
            _ = find_player(self._second_player["name"].split()[0])

    def test_find_player_with_current_season_statistics(self):
        expected_player_goals = self._first_player_current_stats["goals"]
        expected_player_assists = self._first_player_current_stats["assists"]
        expected_player_skill = self._first_player_current_stats["skill"]
        found_player = find_player(self._first_player["telegram_id"])

        self.assertEqual(expected_player_goals, found_player.goals)
        self.assertEqual(expected_player_assists, found_player.assists)
        self.assertEqual(expected_player_skill, found_player.skill)

    def test_find_player_with_all_seasons_statistics(self):
        expected_player_goals = self._first_player_all_stats["goals"]
        expected_player_assists = self._first_player_all_stats["assists"]
        expected_player_skill = self._first_player_all_stats["skill"]
        found_player = find_player(self._first_player["telegram_id"], all_seasons=True)

        self.assertEqual(expected_player_goals, found_player.goals)
        self.assertEqual(expected_player_assists, found_player.assists)
        self.assertEqual(expected_player_skill, found_player.skill)

    def test_find_player_no_skill_tables(self):
        db.model.database.drop_tables([db.model.CurrentSeason, db.model.AllSeasons])
        db.model.database.create_tables([db.model.CurrentSeason, db.model.AllSeasons])

        with self.assertRaises(DbPlayerStatisticsNotFoundError):
            _ = find_player(self._first_player["telegram_id"])

        with self.assertRaises(DbPlayerStatisticsNotFoundError):
            _ = find_player(self._first_player["telegram_id"], all_seasons=True)

    def setUp(self):
        fake.unique.clear()
        self._first_player = create_dict_player()
        self._first_player_current_stats = create_dict_stats(self._first_player["id"])
        self._first_player_all_stats = create_dict_stats(self._first_player["id"])
        self._second_player = create_dict_player()
        self._second_player_current_stats = create_dict_stats(self._second_player["id"])
        self._second_player_all_stats = create_dict_stats(self._second_player["id"])
        # The name of the third player is composed by a new name and the name of the second player
        _second_name = self._second_player["name"].split()
        self._third_player = create_dict_player(name=f"{fake.unique.name()} ({_second_name})")
        self._third_player_current_stats = create_dict_stats(self._third_player["id"])
        self._third_player_all_stats = create_dict_stats(self._third_player["id"])

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
        db.model.Player.insert_many(
            [
                self._first_player,
                self._second_player,
                self._third_player,
            ]
        ).execute()
        db.model.CurrentSeason.insert_many(
            [
                self._first_player_current_stats,
                self._second_player_current_stats,
                self._third_player_current_stats,
            ]
        ).execute()
        db.model.AllSeasons.insert_many(
            [
                self._first_player_all_stats,
                self._second_player_all_stats,
                self._third_player_all_stats,
            ]
        ).execute()

    def tearDown(self):
        db.model.database.close()


class TestCreatePlayer(TestCase):
    def test_create_player_correctly(self):
        pre_count = db.model.Player.select().count()
        create_player(
            name=fake.unique.name(), telegram_id=fake.unique.random_int(), main_player=True
        )
        after_count = db.model.Player.select().count()

        self.assertGreater(after_count, pre_count)

    def test_create_player_without_id_automatically_increases_the_last_one(self):
        new_player_name = fake.unique.name()
        create_player(name=new_player_name, telegram_id=None, main_player=True)

        new_player = db.model.Player.select().where(db.model.Player.name == new_player_name).get()
        self.assertGreater(new_player.telegram_id, self._first_player["telegram_id"])
        self.assertEqual(new_player.telegram_id, self._first_player["telegram_id"] + 1)

    def test_create_player_with_error_due_to_duplication_of_name(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            create_player(name=self._first_player["name"], telegram_id=None, main_player=True)

        self.assertEqual(cm.exception.name, self._first_player["name"])

    def test_create_player_with_error_due_to_duplication_of_id(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            create_player(
                name=fake.unique.name(),
                telegram_id=self._first_player["telegram_id"],
                main_player=True,
            )

        self.assertEqual(cm.exception.identifier, self._first_player["telegram_id"])

    def setUp(self):
        fake.unique.clear()
        self._first_player = create_dict_player()

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
        db.model.Player.insert(**self._first_player).execute()

    def tearDown(self):
        db.model.database.close()


class TestRenamePlayer(TestCase):
    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_rename_player_by_id(self, mock_find_player):
        new_name = fake.unique.name()
        mock_find_player.return_value = db.model.Player.get(
            db.model.Player.id == self._first_player["id"]
        )
        rename_player(player=self._first_player["telegram_id"], new_name=new_name)
        player = db.model.Player.get(db.model.Player.id == self._first_player["id"])

        self.assertEqual(player.name, new_name)

    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_rename_player_by_name(self, mock_find_player):
        new_name = fake.unique.name()
        mock_find_player.return_value = db.model.Player.get(
            db.model.Player.id == self._first_player["id"]
        )
        rename_player(player=self._first_player["name"], new_name=new_name)
        player = db.model.Player.get(db.model.Player.id == self._first_player["id"])

        self.assertEqual(player.name, new_name)

    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_rename_player_with_error_due_to_duplication_of_name(self, mock_find_player):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            mock_find_player.side_effect = [
                db.model.Player.get(db.model.Player.id == self._first_player["id"]),
                db.model.Player.get(db.model.Player.id == self._second_player["id"]),
            ]
            rename_player(
                player=self._first_player["telegram_id"], new_name=self._second_player["name"]
            )

        self.assertEqual(cm.exception.name, self._second_player["name"])
        self.assertEqual(cm.exception.identifier, self._second_player["telegram_id"])

    def setUp(self):
        fake.unique.clear()
        self._first_player = create_dict_player()
        self._second_player = create_dict_player()

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
        db.model.Player.insert_many([self._first_player, self._second_player]).execute()

    def tearDown(self):
        db.model.database.close()


class TestReidPlayer(TestCase):
    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_reid_player_by_id(self, mock_find_player):
        new_identifier = fake.random_int()
        mock_find_player.return_value = db.model.Player.get(
            db.model.Player.id == self._first_player["id"]
        )
        reid_player(player=self._first_player["id"], new_identifier=new_identifier)
        player = db.model.Player.get(db.model.Player.id == self._first_player["id"])

        self.assertEqual(player.telegram_id, new_identifier)

    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_reid_player_by_name(self, mock_find_player):
        new_identifier = fake.random_int()
        mock_find_player.return_value = db.model.Player.get(
            db.model.Player.id == self._first_player["id"]
        )
        reid_player(player=self._first_player["name"], new_identifier=new_identifier)
        player = db.model.Player.get(db.model.Player.id == self._first_player["id"])

        self.assertEqual(player.telegram_id, new_identifier)

    @mock.patch("pyball.legacy.db.utils.find_player")
    def test_reid_player_with_error_due_to_duplication_of_identifier(self, mock_find_player):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            mock_find_player.side_effect = [
                db.model.Player.get(db.model.Player.id == self._first_player["id"]),
                db.model.Player.get(db.model.Player.id == self._second_player["id"]),
            ]
            reid_player(
                player=self._first_player["telegram_id"],
                new_identifier=self._second_player["telegram_id"],
            )

        self.assertEqual(cm.exception.name, self._second_player["name"])
        self.assertEqual(cm.exception.identifier, self._second_player["telegram_id"])

    def setUp(self):
        fake.unique.clear()
        self._first_player = create_dict_player()
        self._second_player = create_dict_player()

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
        db.model.Player.insert_many([self._first_player, self._second_player]).execute()

    def tearDown(self):
        db.model.database.close()


class TestGetPlayerList(TestCase):
    def test_get_player_list_current_seasons(self):
        expected_list = [
            find_player(self._first_player["telegram_id"]),
            find_player(self._second_player["telegram_id"]),
        ]
        obtained_list = get_player_list()

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_id in expected_list:
            self.assertIn(expected_id, obtained_list)

    def test_get_player_list_all_seasons(self):
        expected_list = [
            find_player(self._first_player["telegram_id"], all_seasons=True),
            find_player(self._second_player["telegram_id"], all_seasons=True),
        ]
        obtained_list = get_player_list(all_seasons=True)

        self.assertEqual(len(expected_list), len(obtained_list))

    def test_get_player_id_list(self):
        expected_list = [self._first_player["telegram_id"], self._second_player["telegram_id"]]
        obtained_list = get_player_id_list()

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_id in expected_list:
            self.assertIn(expected_id, obtained_list)

    @classmethod
    def setUpClass(cls):
        fake.unique.clear()
        cls._first_player = create_dict_player()
        cls._first_player_current_stats = create_dict_stats(cls._first_player["id"])
        cls._first_player_all_stats = create_dict_stats(cls._first_player["id"])
        cls._second_player = create_dict_player()
        cls._second_player_current_stats = create_dict_stats(cls._second_player["id"])
        cls._second_player_all_stats = create_dict_stats(cls._second_player["id"])

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
        db.model.Player.insert_many(
            [
                cls._first_player,
                cls._second_player,
            ]
        ).execute()
        db.model.CurrentSeason.insert_many(
            [
                cls._first_player_current_stats,
                cls._second_player_current_stats,
            ]
        ).execute()
        db.model.AllSeasons.insert_many(
            [
                cls._first_player_all_stats,
                cls._second_player_all_stats,
            ]
        ).execute()

    @classmethod
    def tearDownClass(cls):
        db.model.database.close()


class TestGetMatchAndMatchesDateList(TestCase):
    def test_get_matches_date_list_all_seasons(self):
        expected_list = self._dates
        obtained_list = get_matches_date_list(all_seasons=True)

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_date in expected_list:
            self.assertIn(expected_date, obtained_list)

    def test_get_matches_date_list_this_season(self):
        expected_list = self._dates[:0]
        obtained_list = get_matches_date_list(all_seasons=False)

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_date in expected_list:
            self.assertIn(expected_date, obtained_list)

    def test_get_match_not_found(self):
        input_date = fake.unique.date_time()

        with self.assertRaises(DbMatchStatisticsNotFoundError) as cm:
            _ = get_match(input_date)

        self.assertEqual(cm.exception.date, input_date)

    def setUp(self):
        fake.unique.clear()
        # given
        self._players = [
            create_dict_player(skill=6),
            create_dict_player(skill=5),
            create_dict_player(skill=4),
            create_dict_player(skill=3),
        ]
        faker_date = fake.unique.date_time()
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
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._dates[0],
                "player": self._players[3]["id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[0]["id"],
                "team": "Naranja",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": self._dates[1],
                "player": self._players[1]["id"],
                "team": "Naranja",
                "goals": 1,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[2]["id"],
                "team": "Verde",
                "goals": 2,
                "assists": 1,
            },
            {
                "date": self._dates[1],
                "player": self._players[3]["id"],
                "team": "Verde",
                "goals": 1,
                "assists": 2,
            },
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

    def tearDown(self):
        db.model.database.close()


class TestAddMatchResults(TestCase):
    @mock.patch("pyball.legacy.db.utils.backup_database")
    def test_add_match_results_no_statistics(self, _):
        add_match_results([])

    @mock.patch("pyball.legacy.db.utils.backup_database")
    @mock.patch("pyball.legacy.db.utils.PyBallEventBus")
    def test_add_match_results(self, _, __):
        new_match_date = fake.unique.date_time()
        new_match_results = [
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[0]["id"],
                team="Verde",
                goals=2,
                assists=0,
                result="wins",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[1]["id"],
                team="Verde",
                goals=1,
                assists=1,
                result="wins",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[2]["id"],
                team="Naranja",
                goals=0,
                assists=0,
                result="losses",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[3]["id"],
                team="Naranja",
                goals=1,
                assists=0,
                result="losses",
            ),
        ]

        add_match_results(new_match_results)
        obtained_match = get_match(new_match_date)
        matches_date_list = get_matches_date_list(all_seasons=True)

        self.assertEqual(obtained_match["Verde"]["goles"], 3)
        self.assertEqual(obtained_match["Naranja"]["goles"], 1)
        self.assertEqual(len(matches_date_list), 2)

    @mock.patch("pyball.legacy.db.utils.find_player")
    @mock.patch("pyball.legacy.db.utils.backup_database")
    @mock.patch("pyball.legacy.db.utils.PyBallEventBus")
    def test_add_match_results_already_added(self, _, __, mock_find_player):
        mock_find_player.return_value = db.model.Player.get(
            db.model.Player.id == self._match_statistics[0]["player"]
        )

        new_match_results = [
            db.wrapper.MatchStatistic(
                self._match_statistics[0]["date"],
                self._players[4]["id"],
                self._match_statistics[0]["team"],
                self._match_statistics[0]["goals"],
                self._match_statistics[0]["assists"],
            ),
            db.wrapper.MatchStatistic(
                self._match_statistics[0]["date"],
                self._players[5]["id"],
                self._match_statistics[0]["team"],
                self._match_statistics[0]["goals"],
                self._match_statistics[0]["assists"],
            ),
            db.wrapper.MatchStatistic(
                self._match_statistics[0]["date"],
                self._match_statistics[0]["player"],
                self._match_statistics[0]["team"],
                self._match_statistics[0]["goals"],
                self._match_statistics[0]["assists"],
            ),
        ]

        with self.assertRaises(DbStatisticForPlayerInMatchAlreadyExistent) as cm:
            add_match_results(new_match_results)

        self.assertEqual(cm.exception.date, self._match_statistics[0]["date"])
        self.assertEqual(cm.exception.player, self._players[0]["name"])
        matches_date_list = get_matches_date_list(all_seasons=True)
        self.assertEqual(len(matches_date_list), 1)

    def setUp(self):
        fake.unique.clear()
        # given
        self._players = [
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
            create_dict_player(),
        ]
        self._date = fake.unique.date_time()
        self._match_statistics = [
            {
                "date": self._date,
                "player": self._players[0]["id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": self._date,
                "player": self._players[1]["id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 1,
            },
            {
                "date": self._date,
                "player": self._players[2]["id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._date,
                "player": self._players[3]["id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
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

    def tearDown(self):
        db.model.database.close()


@skip("Not yet implemented the new inconsistency work")
class TestCheckInconsistencies(TestCase):
    def test_db_is_consistent(self):
        fake.unique.clear()
        players = [
            create_dict_player(
                goals=3,
                assists=1,
                wins=2,
                losses=0,
                ties=0,
            ),
            create_dict_player(
                goals=1,
                assists=1,
                wins=0,
                losses=2,
                ties=0,
            ),
        ]
        dates = [fake.unique.date_time(), fake.unique.date_time()]
        match_statistics = [
            {
                "date": dates[0],
                "player": players[0]["id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": dates[0],
                "player": players[1]["id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[0]["id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[1]["id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 0,
            },
        ]
        self.initialize_database(players, match_statistics)

        check_inconsistencies()

    def test_db_has_inconsistent_score(self):
        fake.unique.clear()
        players = [
            create_dict_player(
                goals=5,
                assists=1,
                wins=2,
                losses=0,
                ties=0,
            ),
            create_dict_player(
                goals=1,
                assists=1,
                wins=0,
                losses=2,
                ties=0,
            ),
        ]
        dates = [fake.unique.date_time(), fake.unique.date_time()]
        match_statistics = [
            {
                "date": dates[0],
                "player": players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": dates[0],
                "player": players[1]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[0]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 0,
            },
        ]
        self.initialize_database(players, match_statistics)

        with self.assertRaises(DbScoreInconsistencyError):
            check_inconsistencies()

    def test_db_has_inconsistent_wins(self):
        fake.unique.clear()
        players = [
            create_dict_player(
                goals=3,
                assists=1,
                wins=2,
                losses=2,
                ties=0,
            ),
            create_dict_player(
                goals=1,
                assists=1,
                wins=0,
                losses=2,
                ties=0,
            ),
        ]
        dates = [fake.unique.date_time(), fake.unique.date_time()]
        match_statistics = [
            {
                "date": dates[0],
                "player": players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": dates[0],
                "player": players[1]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[0]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 0,
            },
        ]
        self.initialize_database(players, match_statistics)

        with self.assertRaises(DbMatchesCountInconsistencyError):
            check_inconsistencies()

    def initialize_database(self, players: List[dict], statistics: List[dict]) -> None:
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
        db.model.Player.insert_many(players).execute()
        db.model.MatchStatistic.insert_many(statistics).execute()

    def tearDown(self):
        db.model.database.close()


@skip("Not yet implemented the new inconsistency work")
class TestFixInconsistencies(TestCase):
    def test_inconsistent_score_db_is_properly_fixed(self):
        fake.unique.clear()
        players = [
            create_dict_player(
                goals=5,
                assists=1,
                wins=2,
                losses=0,
                ties=0,
            ),
            create_dict_player(
                goals=1,
                assists=1,
                wins=0,
                losses=2,
                ties=0,
            ),
        ]
        dates = [fake.unique.date_time(), fake.unique.date_time()]
        match_statistics = [
            {
                "date": dates[0],
                "player": players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": dates[0],
                "player": players[1]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[0]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 0,
            },
        ]
        self.initialize_database(players, match_statistics)

        with self.assertRaises(DbScoreInconsistencyError):
            check_inconsistencies()

        fix_inconsistencies()

        self.assertEqual(find_player(players[0]["telegram_id"]).goals, 3)
        self.assertNotEqual(find_player(players[0]["telegram_id"]).goals, players[0]["goals"])

    def test_inconsistent_games_db_is_properly_fixed(self):
        fake.unique.clear()
        players = [
            create_dict_player(
                goals=3,
                assists=1,
                wins=2,
                losses=0,
                ties=1,
            ),
            create_dict_player(
                goals=1,
                assists=1,
                wins=0,
                losses=2,
                ties=0,
            ),
        ]
        dates = [fake.unique.date_time(), fake.unique.date_time()]
        match_statistics = [
            {
                "date": dates[0],
                "player": players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": dates[0],
                "player": players[1]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[0]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": dates[1],
                "player": players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 0,
            },
        ]
        self.initialize_database(players, match_statistics)

        with self.assertRaises(DbMatchesCountInconsistencyError):
            check_inconsistencies()

        fix_inconsistencies()

        self.assertEqual(find_player(players[0]["telegram_id"]).ties, 0)
        self.assertNotEqual(find_player(players[0]["telegram_id"]).ties, players[0]["ties"])
        self.assertIsNone(check_inconsistencies())

    def initialize_database(self, players: List[dict], statistics: List[dict]) -> None:
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
        db.model.Player.insert_many(players).execute()
        db.model.MatchStatistic.insert_many(statistics).execute()

    def tearDown(self):
        db.model.database.close()
