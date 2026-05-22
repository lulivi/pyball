# Copyright (c) 2026 Luis Liñán
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
"""Application settings."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def load_app_settings(config_path: Path = Path("config.toml")) -> AppSettings:
    """Load core application settings from TOML config with env var overrides.

    Args:
        config_path: Path to config.toml (defaults to project root)

    Returns:
        AppSettings instance with core configuration loaded.

    Raises:
        SettingsValidationError: If required core settings are missing.
    """
    config: dict = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

    core_cfg = config.get("pyball", {}).get("core", {})

    pyball = CoreSettings(
        location=_get_env_override("core", "location", core_cfg.get("location", "")),
        default_week_day=_get_env_override(
            "core", "default_week_day", core_cfg.get("default_week_day", "wednesday")
        ),
        default_hour=_get_env_override(
            "core", "default_hour", core_cfg.get("default_hour", "20:00")
        ),
        base_url=_get_env_override(
            "core", "base_url", core_cfg.get("base_url", "http://localhost:8000")
        ),
        team_display_names=_parse_team_display_names(
            _get_env_override(
                "core",
                "team_display_names",
                core_cfg.get("team_display_names", ["Claro", "Oscuro"]),
            )
        ),
        locale=_get_env_override("core", "locale", core_cfg.get("locale", "en_US.UTF-8")),
        display_date_format=_get_env_override(
            "core",
            "display_date_format",
            core_cfg.get("display_date_format", "%Y-%m-%d %H:%M"),
        ),
        data_dir=_get_env_override("core", "data_dir", core_cfg.get("data_dir", "data")),
    )

    missing = []
    if not pyball.location:
        missing.append("core.location")
    if missing:
        raise SettingsValidationError(
            f"Faltan parámetros requeridos: {', '.join(missing)}. "
            "Copia example.config.toml a config.toml y completa los valores."
        )

    return AppSettings(pyball=pyball, paths=Paths(_data_dir_override=pyball.data_dir))


def load_settings(config_path: Path = Path("config.toml")) -> Settings:
    """Load settings from TOML config file with env var overrides.

    Args:
        config_path: Path to config.toml (defaults to project root)

    Returns:
        Settings instance with loaded configuration

    Raises:
        SettingsValidationError: If required settings are missing
    """
    LOGS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

    telegram_cfg = config.get("pyball", {}).get("telegram", {})
    core_cfg = config.get("pyball", {}).get("core", {})

    regulars_cfg = telegram_cfg.get("regulars", {})
    substitutes_cfg = telegram_cfg.get("substitutes", {})

    regulars = RegularsChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override(
                "pyball.telegram.regulars", "chat_id", regulars_cfg.get("chat_id", 0)
            )
        ),
        meetups_thread_id=_get_env_override(
            "pyball.telegram.regulars",
            "meetups_thread_id",
            regulars_cfg.get("meetups_thread_id", ""),
        ),
        stats_thread_id=_get_env_override(
            "pyball.telegram.regulars",
            "stats_thread_id",
            regulars_cfg.get("stats_thread_id", ""),
        ),
    )
    substitutes = TelegramChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override(
                "pyball.telegram.substitutes", "chat_id", substitutes_cfg.get("chat_id", 0)
            )
        ),
    )

    management_cfg = telegram_cfg.get("management", {})
    management = ManagementChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override(
                "pyball.telegram.management",
                "chat_id",
                management_cfg.get("chat_id", 0),
            )
        ),
    )

    telegram = TelegramSettings(
        bot_token=_get_env_override(
            "pyball.telegram", "bot_token", telegram_cfg.get("bot_token", "")
        ),
        admins_ids=_parse_admins_ids(
            _get_env_override("pyball.telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
        ),
        regulars=regulars,
        substitutes=substitutes,
        management=management,
    )

    pyball = CoreSettings(
        location=_get_env_override("core", "location", core_cfg.get("location", "")),
        default_week_day=_get_env_override(
            "core", "default_week_day", core_cfg.get("default_week_day", "wednesday")
        ),
        default_hour=_get_env_override(
            "core", "default_hour", core_cfg.get("default_hour", "20:00")
        ),
        base_url=_get_env_override(
            "core", "base_url", core_cfg.get("base_url", "http://localhost:8000")
        ),
        team_display_names=_parse_team_display_names(
            _get_env_override(
                "core",
                "team_display_names",
                core_cfg.get("team_display_names", ["Claro", "Oscuro"]),
            )
        ),
        locale=_get_env_override("core", "locale", core_cfg.get("locale", "en_US.UTF-8")),
        display_date_format=_get_env_override(
            "core",
            "display_date_format",
            core_cfg.get("display_date_format", "%Y-%m-%d %H:%M"),
        ),
        data_dir=_get_env_override("core", "data_dir", core_cfg.get("data_dir", "data")),
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

    return Settings(
        telegram=telegram, pyball=pyball, paths=Paths(_data_dir_override=pyball.data_dir)
    )


LOGS_DIRECTORY_PATH = Path("logs")


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass
class TelegramChatSettings:
    """Base Telegram chat configuration."""

    chat_id: int = 0


@dataclass
class ManagementChatSettings(TelegramChatSettings):
    """Telegram chat configuration for the management channel."""


@dataclass
class RegularsChatSettings(TelegramChatSettings):
    """Telegram chat configuration for the regulars group."""

    meetups_thread_id: str | int = ""
    stats_thread_id: str | int = ""


@dataclass
class TelegramSettings:
    """Telegram bot and chat configuration."""

    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: RegularsChatSettings = field(default_factory=RegularsChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    management: ManagementChatSettings = field(default_factory=ManagementChatSettings)

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids


@dataclass
class CoreSettings:  # pylint: disable=too-many-instance-attributes
    """PyBall-specific configuration."""

    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
    base_url: str = "http://localhost:8000"
    team_display_names: tuple[str, str] = ("Claro", "Oscuro")
    locale: str = "en_US.UTF-8"
    display_date_format: str = "%Y-%m-%d %H:%M"
    data_dir: str = "data"


@dataclass
class Paths:
    """File system paths for data storage."""

    data_dir: Path = field(default_factory=lambda: Path("data"))
    players_file: Path = field(init=False)
    meetups_dir: Path = field(init=False)
    bot_mappings_file: Path = field(init=False)
    bot_messages_file: Path = field(init=False)
    _data_dir_override: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize dependent path fields."""
        if self._data_dir_override:
            self.data_dir = Path(self._data_dir_override)
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"
        self.bot_mappings_file = self.data_dir / "bot" / "telegram-uuid.json"
        self.bot_messages_file = self.data_dir / "bot" / "messages.json"


@dataclass
class AppSettings:
    """Base application settings with core and path configuration."""

    pyball: CoreSettings = field(default_factory=CoreSettings)
    paths: Paths = field(default_factory=Paths)


@dataclass
class Settings:
    """Application settings container."""

    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pyball: CoreSettings = field(default_factory=CoreSettings)
    paths: Paths = field(default_factory=Paths)


def _parse_team_display_names(value) -> tuple[str, str]:
    """Parse team_display_names from config list or comma-separated env string."""
    if isinstance(value, list) and len(value) == 2:
        return (str(value[0]), str(value[1]))
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) == 2:
            return (parts[0], parts[1])
    return ("Claro", "Oscuro")


def _parse_chat_id(value) -> int:
    """Parse chat_id from config or env, handling empty strings."""
    if isinstance(value, str) and not value:
        return 0
    return int(value)


def _parse_admins_ids(value) -> tuple[int, ...]:
    """Parse admins_ids from config or env override."""
    if isinstance(value, list):
        return tuple(int(x) for x in value)
    if isinstance(value, str):
        return tuple(int(x.strip()) for x in value.split(",") if x.strip())
    return ()


def _get_env_override(section: str, key: str, default):
    """Get environment variable override for config value.

    Env var format: PYBALL_<SECTION>_<KEY>
    Example: PYBALL_TELEGRAM_BOT_TOKEN, PYBALL_CORE_LOCATION

    The section maps from TOML to env var:
    - "pyball.telegram" -> "telegram"
    - "pyball.telegram.regulars" -> "telegram.regulars"
    - "pyball.telegram.substitutes" -> "telegram.substitutes"
    - "core" -> "core"
    """
    section_for_env = section.replace("pyball.", "")
    env_key = f"PYBALL_{section_for_env.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is None:
        return default
    return env_value
