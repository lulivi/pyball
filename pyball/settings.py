"""Application settings."""

import os
import tomllib

from dataclasses import dataclass, field
from pathlib import Path


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass
class Paths:
    """File system paths for data storage."""

    data_dir: Path = field(default_factory=lambda: Path("data"))
    players_file: Path = field(init=False)
    meetups_dir: Path = field(init=False)
    bot_mappings_file: Path = field(init=False)
    bot_messages_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"
        self.bot_mappings_file = self.data_dir / "bot" / "mappings.json"
        self.bot_messages_file = self.data_dir / "bot" / "messages.json"


LOGS_DIRECTORY_PATH = Path("logs")


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


def _parse_chat_id(value) -> int:
    """Parse chat_id from config or env, handling empty strings."""
    if isinstance(value, str) and not value:
        return 0
    return int(value)


@dataclass
class TelegramChatSettings:
    """Telegram chat configuration for regulars or substitutes."""

    chat_id: int = 0
    thread_id: str | int = ""

    def has_thread(self) -> bool:
        """Check if a thread ID is configured."""
        return bool(self.thread_id)


@dataclass
class TelegramSettings:
    """Telegram bot and chat configuration."""

    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids


@dataclass
class PyballSettings:
    """PyBall-specific configuration."""

    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
    base_url: str = "http://localhost:8000"


@dataclass
class LocaleSettings:
    """Locale configuration."""

    value: str = "en_US.UTF-8"


@dataclass
class Settings:
    """Application settings container."""

    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pyball: PyballSettings = field(default_factory=PyballSettings)
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
    pyball_cfg = config.get("pyball", {})
    locale_cfg = config.get("locale", {})

    regulars_cfg = telegram_cfg.get("regulars", {})
    substitutes_cfg = telegram_cfg.get("substitutes", {})

    regulars = TelegramChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override("telegram_regulars", "chat_id", regulars_cfg.get("chat_id", 0))
        ),
        thread_id=_get_env_override(
            "telegram_regulars", "thread_id", regulars_cfg.get("thread_id", "")
        ),
    )
    substitutes = TelegramChatSettings(
        chat_id=_parse_chat_id(
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

    pyball = PyballSettings(
        location=_get_env_override("pyball", "location", pyball_cfg.get("location", "")),
        default_week_day=_get_env_override(
            "pyball", "default_week_day", pyball_cfg.get("default_week_day", "wednesday")
        ),
        default_hour=_get_env_override(
            "pyball", "default_hour", pyball_cfg.get("default_hour", "20:00")
        ),
        base_url=_get_env_override(
            "pyball", "base_url", pyball_cfg.get("base_url", "http://localhost:8000")
        ),
    )

    missing = []
    if not telegram.bot_token:
        missing.append("telegram.bot_token")
    if not pyball.location:
        missing.append("pyball.location")
    if not telegram.regulars.chat_id:
        missing.append("telegram.regulars.chat_id")
    if not telegram.substitutes.chat_id:
        missing.append("telegram.substitutes.chat_id")

    if missing:
        raise SettingsValidationError(
            f"Faltan parámetros requeridos: {', '.join(missing)}. "
            "Copia example.config.toml a config.toml y completa los valores."
        )

    locale = LocaleSettings(
        value=_get_env_override("locale", "value", locale_cfg.get("value", "en_US.UTF-8")),
    )

    return Settings(telegram=telegram, pyball=pyball, locale=locale)
