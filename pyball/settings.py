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

    pyball = PyballConfig(
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


LOGS_DIRECTORY_PATH = Path("logs")


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass
class PyballConfig:  # pylint: disable=too-many-instance-attributes
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
    _data_dir_override: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize dependent path fields."""
        if self._data_dir_override:
            self.data_dir = Path(self._data_dir_override)
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"


@dataclass
class AppSettings:
    """Base application settings with core and path configuration."""

    pyball: PyballConfig = field(default_factory=PyballConfig)
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
