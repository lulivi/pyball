"""Application settings."""

from dataclasses import dataclass, field
from pathlib import Path


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
    bot_token: str = ""


@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    paths: Paths = field(default_factory=Paths)


def load_settings() -> Settings:
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, value = line.strip().split("=", 1)
                    import os
                    os.environ.setdefault(key, value)
    return Settings()
