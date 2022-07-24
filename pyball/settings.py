"""Populate the configuration variables from the environment."""
from decouple import config

BOT_TOKEN: str = config("BOT_TOKEN")
