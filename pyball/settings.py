"""Application settings."""

import os
import tomllib

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


def _get_env_override(section: str, key: str, default):
    """Get environment variable override for config value.

    Env var format: PYBALL_<SECTION>_<KEY>
    Example: PYBALL_TELEGRAM_BOT_TOKEN
    """
    env_key = f"PYBALL_{section.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is None:
        return default
    return env_value


def _parse_admins_ids(value) -> tuple[int, ...]:
    """Parse admins_ids from config or env override."""
    if isinstance(value, list):
        return tuple(int(x) for x in value)
    if isinstance(value, str):
        return tuple(int(x.strip()) for x in value.split(",") if x.strip())
    return ()


@dataclass
class TelegramChatSettings:
    chat_id: int = 0
    thread_id: str | int = ""

    def has_thread(self) -> bool:
        return bool(self.thread_id)


@dataclass
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids


@dataclass
class LocaleSettings:
    value: str = "en_US.UTF-8"


@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)


def load_settings(config_path: Path = Path("config.toml")) -> Settings:
    """Load settings from TOML config file with env var overrides.

    Args:
        config_path: Path to config.toml (defaults to project root)

    Returns:
        Settings instance with loaded configuration

    Raises:
        SettingsValidationError: If required settings are missing
    """
    example_path = Path("example.config.toml")

    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    elif example_path.exists():
        with open(example_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}

    telegram_cfg = config.get("telegram", {})
    locale_cfg = config.get("locale", {})

    regulars_cfg = telegram_cfg.get("regulars", {})
    substitutes_cfg = telegram_cfg.get("substitutes", {})

    regulars = TelegramChatSettings(
        chat_id=int(
            _get_env_override("telegram_regulars", "chat_id", regulars_cfg.get("chat_id", 0))
        ),
        thread_id=_get_env_override(
            "telegram_regulars", "thread_id", regulars_cfg.get("thread_id", "")
        ),
    )
    substitutes = TelegramChatSettings(
        chat_id=int(
            _get_env_override("telegram_substitutes", "chat_id", substitutes_cfg.get("chat_id", 0))
        ),
        thread_id=_get_env_override(
            "telegram_substitutes", "thread_id", substitutes_cfg.get("thread_id", "")
        ),
    )

    telegram = TelegramSettings(
        bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
        admins_ids=_parse_admins_ids(
            _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
        ),
        regulars=regulars,
        substitutes=substitutes,
    )

    if not telegram.bot_token:
        raise SettingsValidationError("bot_token is required but not set")

    locale = LocaleSettings(
        value=_get_env_override("locale", "value", locale_cfg.get("value", "en_US.UTF-8")),
    )

    return Settings(telegram=telegram, locale=locale)
