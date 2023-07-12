# Copyright (c) 2022 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Create the database schema."""

import argparse

from pathlib import Path

from peewee import SqliteDatabase

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

try:
    from pyball.db.model import MatchStatistic, Player, database
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(REPOSITORY_ROOT))

from pyball.settings import DATABASE_FILE_PATH


def re_create_database(database_path: Path) -> None:
    database.initialize(SqliteDatabase(database_path))
    database.connect()
    database.drop_tables([Player, MatchStatistic])
    database.create_tables([Player, MatchStatistic])
    database.close()


def migrate_database(from_database: Path, to_database: Path) -> None:
    database.initialize(SqliteDatabase(from_database))
    database.connect()
    players = list(Player.select().dicts())
    matches = list(MatchStatistic.select().dicts())
    database.close()

    database.initialize(SqliteDatabase(to_database))
    database.connect()
    Player.insert_many(players).execute()
    MatchStatistic.insert_many(matches).execute()
    database.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog=Path(__file__).name, description="Create or clean the database.")
    parser.add_argument("--migrate-from", type=Path, help="Database from which migrate the rows")
    args = parser.parse_args()

    re_create_database(DATABASE_FILE_PATH)

    if args.migrate_from is not None:
        print(f"Migrating data from {args.migrate_from} to {DATABASE_FILE_PATH}")
        migrate_database(args.migrate_from, DATABASE_FILE_PATH)


if __name__ == "__main__":
    main()
