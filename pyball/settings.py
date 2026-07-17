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
from typing import cast


def load_app_settings(config_path: Path = Path("config.toml")) -> AppSettings:
    """Load core application settings from TOML config with env var overrides.

    Args:
        config_path: Path to config.toml (defaults to project root)

    Returns:
        AppSettings instance with core configuration loaded.

    Raises:
        SettingsValidationError: If required core settings are missing.
    """
    if not config_path.exists():
        raise SettingsValidationError(
            f"No se encontró el archivo de configuración: '{config_path}'. "
            "Ejecuta 'pyball --bootstrap' o 'pyball-telegram --bootstrap' para generar "
            "un config.toml de ejemplo."
        )
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    core_cfg = config.get("pyball", {}).get("core", {})

    core_keys = (
        "location",
        "name",
        "default_week_day",
        "default_hour",
        "base_url",
        "team_colors",
        "locale",
        "display_date_format",
        "data_dir",
        "api_port",
        "match_token",
        "manage_token",
        "signup_token",
        "enable_web_signup",
        "theme_color",
        "icons_dir",
    )
    raw = {k: _get_env_override("core", k, core_cfg.get(k)) for k in core_keys}
    raw["match_token"] = raw["match_token"] or ""
    raw["manage_token"] = raw["manage_token"] or ""
    raw["signup_token"] = raw["signup_token"] or ""
    raw["enable_web_signup"] = raw["enable_web_signup"] or False
    raw["theme_color"] = raw["theme_color"] or "#0f172a"
    raw["icons_dir"] = raw["icons_dir"] or ""

    missing = [f"core.{k}" for k, v in raw.items() if v is None]
    if raw.get("location") is not None and not raw["location"]:
        missing.append("core.location (está vacío)")
    if raw.get("name") is not None and not raw["name"]:
        missing.append("core.name (está vacío)")
    if missing:
        raise SettingsValidationError(
            f"Faltan parámetros requeridos: {', '.join(missing)}. "
            "Ejecuta 'pyball --bootstrap' o 'pyball-telegram --bootstrap' para generar "
            "un config.toml de ejemplo."
        )

    pyball = PyballConfig(
        location=raw["location"],
        name=raw["name"],
        default_week_day=raw["default_week_day"],
        default_hour=raw["default_hour"],
        base_url=raw["base_url"],
        team_colors=_parse_team_colors(raw["team_colors"]),
        locale=raw["locale"],
        display_date_format=raw["display_date_format"],
        data_dir=raw["data_dir"],
        api_port=_parse_api_port(raw["api_port"]),
        match_token=raw["match_token"],
        manage_token=raw["manage_token"],
        signup_token=raw["signup_token"],
        enable_web_signup=_parse_bool(raw["enable_web_signup"]),
        theme_color=raw["theme_color"],
        icons_dir=raw["icons_dir"],
    )

    return AppSettings(pyball=pyball, paths=Paths(_data_dir_override=pyball.data_dir))


LOGS_DIRECTORY_PATH = Path("logs")

COLOR_PALETTE: dict[str, dict[str, str]] = {
    # Colores disponibles: blanco ⚪  negro ⚫  rojo 🔴  naranja 🟠  amarillo 🟡
    #                      verde 🟢  azul 🔵  morado 🟣  marron 🟤
    "blanco": {"bg": "#e4e4e7", "text": "#27272a", "emoji": "⚪"},
    "negro": {"bg": "#27272a", "text": "#e4e4e7", "emoji": "⚫"},
    "rojo": {"bg": "#b91c1c", "text": "#fff1f2", "emoji": "🔴"},
    "naranja": {"bg": "#ea580c", "text": "#ffffff", "emoji": "🟠"},
    "amarillo": {"bg": "#fbbf24", "text": "#422006", "emoji": "🟡"},
    "verde": {"bg": "#16a34a", "text": "#f0fdf4", "emoji": "🟢"},
    "azul": {"bg": "#1d4ed8", "text": "#eff6ff", "emoji": "🔵"},
    "morado": {"bg": "#7e22ce", "text": "#faf5ff", "emoji": "🟣"},
    "marron": {"bg": "#92400e", "text": "#fef3c7", "emoji": "🟤"},
}


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass
class PyballConfig:  # pylint: disable=too-many-instance-attributes
    """PyBall-specific configuration."""

    location: str = ""
    name: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
    base_url: str = "http://localhost:8000"
    api_port: int = 8000
    team_colors: tuple[str, str, str] = ("blanco", "negro", "rojo")
    team_emojis: tuple[str, str, str] = field(init=False)
    team_hex_bg: tuple[str, str, str] = field(init=False)
    team_hex_text: tuple[str, str, str] = field(init=False)
    locale: str = "en_US.UTF-8"
    display_date_format: str = "%Y-%m-%d %H:%M"
    data_dir: str = "data"
    match_token: str = ""
    manage_token: str = ""
    signup_token: str = ""
    enable_web_signup: bool = False
    theme_color: str = "#0f172a"
    icons_dir: str = ""

    def __post_init__(self) -> None:
        """Resolve team_colors into derived emoji and hex fields."""
        for color_name in self.team_colors:
            if color_name not in COLOR_PALETTE:
                valid = ", ".join(COLOR_PALETTE)
                raise ValueError(f"Color de equipo desconocido: '{color_name}'. Opciones: {valid}")
        self.team_emojis = cast(
            "tuple[str, str, str]", tuple(COLOR_PALETTE[c]["emoji"] for c in self.team_colors)
        )
        self.team_hex_bg = cast(
            "tuple[str, str, str]", tuple(COLOR_PALETTE[c]["bg"] for c in self.team_colors)
        )
        self.team_hex_text = cast(
            "tuple[str, str, str]", tuple(COLOR_PALETTE[c]["text"] for c in self.team_colors)
        )


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


def _parse_api_port(value) -> int:
    """Parse api_port from config int or env var string."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 8000


def _parse_bool(value) -> bool:
    """Parse enable_web_signup from a native TOML bool or an env var string."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def _parse_team_colors(value) -> tuple[str, str, str]:
    """Parse team_colors from config list or comma-separated env string."""
    if isinstance(value, list) and len(value) == 3:
        return (
            str(value[0]).strip().lower(),
            str(value[1]).strip().lower(),
            str(value[2]).strip().lower(),
        )
    if isinstance(value, str):
        parts = [p.strip().lower() for p in value.split(",") if p.strip()]
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
    return ("blanco", "negro", "rojo")


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
