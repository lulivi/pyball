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

from decouple import Csv, config

LOCALE: str = config("LOCALE", default="es_ES.UTF-8")
BOT_TOKEN: str = config("BOT_TOKEN")
SUBSTITUTES_ID: str = config("SUBSTITUTES_ID")
ADMINS_IDS: Tuple[str] = config("ADMINS_IDS", cast=Csv(int, post_process=tuple), default="")
PERSISTENCE_FILE_PATH: Path = config(
    "PERSISTENCE_FILE_PATH",
    cast=Path,
    default=Path(__file__).resolve().parents[1].joinpath("bot.persistence"),
)
