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
