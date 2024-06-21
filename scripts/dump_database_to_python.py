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

"""Export the database data."""

import datetime

from pathlib import Path

from peewee import SqliteDatabase

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

try:
    from pyball.legacy.db.model import MatchStatistic, Player, database
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(REPOSITORY_ROOT))
    from pyball.legacy.db.model import MatchStatistic, Player, database

from pyball.settings import DATABASE_FILE_PATH


def main() -> None:
    time_format = "%Y_%m_%d"
    database.initialize(SqliteDatabase(str(DATABASE_FILE_PATH)))
    database.connect()
    if database.get_tables():
        players, stats = list(Player.select().dicts()), list(MatchStatistic.select().dicts())
        with open(
            DATABASE_FILE_PATH.with_name(
                f"{datetime.datetime.now().strftime(time_format)}_players.py"
            ),
            "w",
        ) as f_players, open(
            DATABASE_FILE_PATH.with_name(
                f"{datetime.datetime.now().strftime(time_format)}_stats.py"
            ),
            "w",
        ) as f_stats:
            f_players.write(f"db.model.Player.insert_many({str(players)})")
            f_stats.write(f"db.model.MatchStatistic.insert_many({str(stats)})")
    else:
        print("No hay tablas creadas en la base de datos.")
    database.close()


if __name__ == "__main__":
    main()
