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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="create_database", description="Create or clean the database."
    )
    parser.add_argument("--force", action="store_true", help="Force the tables deletion")
    args = parser.parse_args()

    database.initialize(SqliteDatabase(str(DATABASE_FILE_PATH)))
    database.connect()
    if args.force:
        database.drop_tables([Player, MatchStatistic])
    elif database.get_tables():
        print("There are existing tables in the database, use the option --force to clean them.")
    database.create_tables([Player, MatchStatistic])
    database.close()


if __name__ == "__main__":
    main()
