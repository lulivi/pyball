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

"""Populate the configuration variables from the environment."""

from pathlib import Path
from typing import Tuple

from decouple import AutoConfig, Csv

APP_ROOT_DIR: Path = Path.cwd()
config = AutoConfig(search_path=APP_ROOT_DIR)
LOCALE: str = config("LOCALE", default="es_ES.UTF-8")
DATE_FORMAT: str = config("DATE_FORMAT", default="%d/%b/%Y")
TIME_FORMAT: str = config("TIME_FORMAT", default="%H:%M")
DATETIME_FORMAT: str = config("DATETIME_FORMAT", default=f"{DATE_FORMAT} {TIME_FORMAT}")
BOT_TOKEN: str = config("BOT_TOKEN")
REGULARS_ID: int = config("REGULARS_ID", cast=int)
SUBSTITUTES_ID: int = config("SUBSTITUTES_ID", cast=int)
DEFAULT_MATCH_LOCATION: str = config("DEFAULT_MATCH_LOCATION")
ADMINS_IDS: Tuple[str] = config("ADMINS_IDS", cast=Csv(int, post_process=tuple), default="")
LOGS_DIRECTORY_PATH: Path = config(
    "LOGS_DIRECTORY_PATH",
    cast=Path,
    default=APP_ROOT_DIR.joinpath("logs"),
)
LOGS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIRECTORY_PATH: Path = config(
    "DATA_DIRECTORY_PATH",
    cast=Path,
    default=APP_ROOT_DIR.joinpath("data"),
)
DATA_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
DATABASE_FILE_PATH: Path = config(
    "DATABASE_FILE_PATH",
    cast=Path,
    default=DATA_DIRECTORY_PATH.joinpath("pyball.db"),
)
