"""Application settings."""

import os
from dataclasses import dataclass, field
from pathlib import Path


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""
    pass


@dataclass
class Paths:
    data_dir: Path = field(default_factory=lambda: Path("data"))
    players_file: Path = field(init=False)
    meetups_dir: Path = field(init=False)
    mappings_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"
        self.mappings_file = self.data_dir / "bot" / "mappings.json"


@dataclass
class TelegramSettings:
    bot_token: str = field(default_factory=lambda: os.environ.get("bot_token", ""))

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise SettingsValidationError("bot_token is required but not set in .env file")


@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    paths: Paths = field(default_factory=Paths)


def load_settings() -> Settings:
    """Load settings from .env file and environment variables.
    
    Parses .env file, setting values in environment.
    Validates that required settings (e.g., bot_token) are present.
    
    Raises:
        SettingsValidationError: If required settings are missing.
    """
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in line:
                    raise SettingsValidationError(f"Malformed line {line_num} in .env: missing '=' separator")
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip().lower(), value.strip())
    return Settings()
