from typing import List
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
from tests.utils import create_dict_player

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


class TestFindPlayer(TestCase):
    def test_find_player_by_id(self):
        expected_player_id = self._first_id
        expected_player_name = self._first_name
        player = find_player(self._first_id)

        self.assertEqual(player.telegram_id, expected_player_id)
        self.assertEqual(player.name, expected_player_name)

    def test_find_player_by_name(self):
        expected_player_id = self._first_id
        expected_player_name = self._first_name
        player = find_player(self._first_name)

        self.assertEqual(player.telegram_id, expected_player_id)
        self.assertEqual(player.name, expected_player_name)

    def test_find_player_when_name_not_existent(self):
        with self.assertRaises(DbPlayerNotFoundError):
            _ = find_player(fake.name())

    def test_find_player_when_id_not_existent(self):
        with self.assertRaises(DbPlayerNotFoundError):
            _ = find_player(fake.random_int())

    def test_find_player_when_multiple_found(self):
        with self.assertRaises(DbMultiplePlayersFoundError):
            # Since the name of the third player is composed by the name of the second player,
            # if only one word of the name is provided, it will find the two players.
            _ = find_player(self._second_name.split()[0])

    @classmethod
    def setUpClass(self):
        self._first_id = fake.random_int()
        self._first_name = fake.name()
        self._second_id = fake.random_int()
        self._second_name = fake.name()
        self._third_id = fake.random_int()
        # The name of the third player is composed by a new name and the name of the second player
        self._third_name = f"{fake.name()} ({self._second_name.split()})"

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(
            [
                [self._first_id, self._first_name, True],
                [self._second_id, self._second_name, True],
                [self._third_id, self._third_name, True],
            ],
            fields=[db.model.Player.telegram_id, db.model.Player.name, db.model.Player.main],
        ).execute()

    @classmethod
    def tearDownClass(self):
        db.model.database.close()


class TestCreatePlayer(TestCase):
    def test_create_player_correctly(self):
        pre_count = db.model.Player.select().count()
        create_player(player_name=fake.name(), player_id=fake.random_int(), main_player=True)
        after_count = db.model.Player.select().count()

        self.assertGreater(after_count, pre_count)

    def test_create_player_without_id_automatically_increases_the_last_one(self):
        new_player_name = fake.name()
        create_player(player_name=new_player_name, player_id=None, main_player=True)

        new_player = find_player(new_player_name)
        self.assertGreater(new_player.telegram_id, self._first_id)
        self.assertEqual(new_player.telegram_id, self._first_id + 1)

    def test_create_player_with_error_due_to_duplication_of_name(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            create_player(player_name=self._first_name, player_id=None, main_player=True)

        self.assertEqual(cm.exception.name, self._first_name)

    def test_create_player_with_error_due_to_duplication_of_id(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            create_player(player_name=fake.name(), player_id=self._first_id, main_player=True)

        self.assertEqual(cm.exception.identifier, self._first_id)

    def setUp(self):
        self._first_id = fake.random_int()
        self._first_name = fake.name()

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert(
            telegram_id=self._first_id, name=self._first_name, main=True
        ).execute()

    def tearDown(self):
        db.model.database.close()


class TestRenamePlayer(TestCase):
    def test_rename_player_by_id(self):
        new_name = fake.name()
        rename_player(player=self._a_player_id, new_name=new_name)
        player = find_player(self._a_player_id)

        self.assertEqual(player.name, new_name)

    def test_rename_player_by_name(self):
        new_name = fake.name()
        rename_player(player=self._a_player_name, new_name=new_name)
        player = find_player(self._a_player_id)

        self.assertEqual(player.name, new_name)

    def test_rename_player_with_error_due_to_duplication_of_name(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            rename_player(player=self._a_player_id, new_name=self._b_player_name)

        self.assertEqual(cm.exception.name, self._b_player_name)
        self.assertEqual(cm.exception.identifier, self._b_player_id)

    def setUp(self):
        self._a_player_id = fake.random_int()
        self._a_player_name = fake.name()
        print(self._a_player_id, self._a_player_name, sep=" | ")
        self._b_player_id = fake.random_int()
        self._b_player_name = fake.name()
        print(self._b_player_id, self._b_player_name, sep=" | ")

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert(
            telegram_id=self._a_player_id, name=self._a_player_name, main=True
        ).execute()
        db.model.Player.insert(
            telegram_id=self._b_player_id, name=self._b_player_name, main=True
        ).execute()

    def tearDown(self):
        db.model.database.close()


class TestReidPlayer(TestCase):
    def test_reid_player_by_id(self):
        new_identifier = fake.random_int()
        reid_player(player=self._a_player_id, new_identifier=new_identifier)
        player = find_player(self._a_player_name)

        self.assertEqual(player.telegram_id, new_identifier)

    def test_reid_player_by_name(self):
        new_identifier = fake.random_int()
        reid_player(player=self._a_player_name, new_identifier=new_identifier)
        player = find_player(self._a_player_name)

        self.assertEqual(player.telegram_id, new_identifier)

    def test_reid_player_with_error_due_to_duplication_of_identifier(self):
        with self.assertRaises(DbPlayerAlreadyExistentError) as cm:
            reid_player(player=self._a_player_id, new_identifier=self._b_player_id)

        self.assertEqual(cm.exception.name, self._b_player_name)
        self.assertEqual(cm.exception.identifier, self._b_player_id)

    def setUp(self):
        self._a_player_id = fake.random_int()
        self._a_player_name = fake.name()
        print(self._a_player_id, self._a_player_name, sep=" | ")
        self._b_player_id = fake.random_int()
        self._b_player_name = fake.name()
        print(self._b_player_id, self._b_player_name, sep=" | ")

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert(
            telegram_id=self._a_player_id, name=self._a_player_name, main=True
        ).execute()
        db.model.Player.insert(
            telegram_id=self._b_player_id, name=self._b_player_name, main=True
        ).execute()

    def tearDown(self):
        db.model.database.close()


class TestGetPlayerList(TestCase):
    def test_get_player_list(self):
        expected_list = [find_player(self._a_player_id), find_player(self._b_player_id)]
        obtained_list = get_player_list()

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_id in expected_list:
            self.assertIn(expected_id, obtained_list)

    def test_get_player_id_list(self):
        expected_list = [self._a_player_id, self._b_player_id]
        obtained_list = get_player_id_list()

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_id in expected_list:
            self.assertIn(expected_id, obtained_list)

    @classmethod
    def setUpClass(cls):
        cls._a_player_id = fake.random_int()
        cls._a_player_name = fake.name()
        print(cls._a_player_id, cls._a_player_name, sep=" | ")
        cls._b_player_id = fake.random_int()
        cls._b_player_name = fake.name()
        print(cls._b_player_id, cls._b_player_name, sep=" | ")

        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert(
            telegram_id=cls._a_player_id, name=cls._a_player_name, main=True
        ).execute()
        db.model.Player.insert(
            telegram_id=cls._b_player_id, name=cls._b_player_name, main=True
        ).execute()

    @classmethod
    def tearDownClass(cls):
        db.model.database.close()


class TestGetMatchAndMatchesDateList(TestCase):
    def test_get_matches_date_list(self):
        expected_list = self._dates
        obtained_list = get_matches_date_list()

        self.assertEqual(len(expected_list), len(obtained_list))

        for expected_date in expected_list:
            self.assertIn(expected_date, obtained_list)

    def test_get_match_not_found(self):
        input_date = fake.unique.date_time()

        with self.assertRaises(DbMatchStatisticsNotFoundError) as cm:
            _ = get_match(input_date)

        self.assertEqual(cm.exception.date, input_date)

    def setUp(self):
        # given
        fake.unique.clear()
        self._players = [
            create_dict_player(skill=6),
            create_dict_player(skill=5),
            create_dict_player(skill=4),
            create_dict_player(skill=3),
        ]
        self._dates = [fake.unique.date_time(), fake.unique.date_time()]
        self._match_statistics = [
            {
                "date": self._dates[0],
                "player": self._players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": self._dates[0],
                "player": self._players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 1,
            },
            {
                "date": self._dates[0],
                "player": self._players[2]["telegram_id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._dates[0],
                "player": self._players[3]["telegram_id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 1,
                "assists": 1,
            },
            {
                "date": self._dates[1],
                "player": self._players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 1,
                "assists": 0,
            },
            {
                "date": self._dates[1],
                "player": self._players[2]["telegram_id"],
                "team": "Verde",
                "goals": 2,
                "assists": 1,
            },
            {
                "date": self._dates[1],
                "player": self._players[3]["telegram_id"],
                "team": "Verde",
                "goals": 1,
                "assists": 2,
            },
        ]
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(self._players).execute()
        db.model.MatchStatistic.insert_many(self._match_statistics).execute()

    def tearDown(self):
        db.model.database.close()


class TestAddMatchResults(TestCase):
    @mock.patch("pyball.db.utils.backup_database")
    def test_add_match_results(self, _):
        new_match_date = fake.unique.date_time()
        new_match_results = [
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[0]["telegram_id"],
                team="Verde",
                goals=2,
                assists=0,
                result="wins",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[1]["telegram_id"],
                team="Verde",
                goals=1,
                assists=1,
                result="wins",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[2]["telegram_id"],
                team="Naranja",
                goals=0,
                assists=0,
                result="losses",
            ),
            db.wrapper.MatchStatistic(
                date=new_match_date,
                player=self._players[3]["telegram_id"],
                team="Naranja",
                goals=1,
                assists=0,
                result="losses",
            ),
        ]

        add_match_results(new_match_results)
        obtained_match = get_match(new_match_date)
        matches_date_list = get_matches_date_list()

        self.assertEqual(obtained_match["Verde"]["goles"], 3)
        self.assertEqual(obtained_match["Naranja"]["goles"], 1)
        self.assertEqual(len(matches_date_list), 2)

    @mock.patch("pyball.db.utils.backup_database")
    def test_add_match_results_already_added(self, _):
        new_match_results = [
            db.wrapper.MatchStatistic(
                self._match_statistics[0]["date"],
                self._players[4]["telegram_id"],
                self._match_statistics[0]["team"],
                self._match_statistics[0]["goals"],
                self._match_statistics[0]["assists"],
            ),
            db.wrapper.MatchStatistic(
                self._match_statistics[0]["date"],
                self._players[5]["telegram_id"],
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

        with self.assertRaises(DbStatisticForPlayerInMatchAlreadyExistent):
            add_match_results(new_match_results)

        matches_date_list = get_matches_date_list()
        self.assertEqual(len(matches_date_list), 1)

    def setUp(self):
        # given
        fake.unique.clear()
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
                "player": self._players[0]["telegram_id"],
                "team": "Naranja",
                "goals": 2,
                "assists": 0,
            },
            {
                "date": self._date,
                "player": self._players[1]["telegram_id"],
                "team": "Naranja",
                "goals": 0,
                "assists": 1,
            },
            {
                "date": self._date,
                "player": self._players[2]["telegram_id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
            {
                "date": self._date,
                "player": self._players[3]["telegram_id"],
                "team": "Verde",
                "goals": 0,
                "assists": 0,
            },
        ]
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(self._players).execute()
        db.model.MatchStatistic.insert_many(self._match_statistics).execute()

    def tearDown(self):
        db.model.database.close()


class TestUpdatePlayerSkill(TestCase):
    def test_update_player_skill(self):
        players = [
            create_dict_player(
                goals=5,
                assists=2,
                wins=3,
                losses=0,
                ties=1,
            ),
            create_dict_player(
                goals=2,
                assists=1,
                wins=2,
                losses=1,
                ties=1,
            ),
            create_dict_player(
                goals=1,
                assists=0,
                wins=0,
                losses=3,
                ties=1,
            ),
        ]
        self.initialize_players(players)

        update_players_skill()

        self.assertGreater(
            find_player(players[0]["telegram_id"]).skill,
            find_player(players[1]["telegram_id"]).skill,
        )
        self.assertGreater(
            find_player(players[1]["telegram_id"]).skill,
            find_player(players[2]["telegram_id"]).skill,
        )

    def test_update_player_skill_with_no_goals_or_assists(self):
        players = [
            create_dict_player(
                goals=0,
                assists=0,
                wins=0,
                losses=0,
                ties=0,
            ),
            create_dict_player(
                goals=0,
                assists=0,
                wins=0,
                losses=0,
                ties=0,
            ),
            create_dict_player(
                goals=0,
                assists=0,
                wins=0,
                losses=0,
                ties=0,
            ),
        ]
        self.initialize_players(players)

        self.assertEqual(
            find_player(players[0]["telegram_id"]).skill,
            find_player(players[1]["telegram_id"]).skill,
        )
        self.assertEqual(
            find_player(players[1]["telegram_id"]).skill,
            find_player(players[2]["telegram_id"]).skill,
        )

    def initialize_players(self, players: List[dict]) -> None:
        db.model.database.initialize(peewee.SqliteDatabase(":memory:"))
        db.model.database.connect()
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(players).execute()

    def tearDown(self):
        db.model.database.close()


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
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(players).execute()
        db.model.MatchStatistic.insert_many(statistics).execute()

    def tearDown(self):
        db.model.database.close()


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
        db.model.database.create_tables([db.model.Player, db.model.MatchStatistic])
        db.model.Player.insert_many(players).execute()
        db.model.MatchStatistic.insert_many(statistics).execute()

    def tearDown(self):
        db.model.database.close()
