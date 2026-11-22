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
"""Telegram-specific application settings."""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pyball.settings import AppSettings, SettingsValidationError

logger = logging.getLogger(__name__)


@dataclass
class ChatConfig:
    """A single Telegram message destination: a chat and an optional forum topic."""

    chat_id: int = 0
    message_thread_id: int | None = None

    def __bool__(self) -> bool:
        """Return True when a chat is configured (chat_id is non-zero)."""
        return bool(self.chat_id)


@dataclass
class RegularsChats:
    """Message destinations for the regulars audience."""

    meetups: ChatConfig = field(default_factory=ChatConfig)
    stats: ChatConfig = field(default_factory=ChatConfig)


@dataclass
class SubstitutesChats:
    """Message destinations for the substitutes audience."""

    meetups: ChatConfig = field(default_factory=ChatConfig)


@dataclass
class ManagementChats:
    """Message destinations for management output."""

    activity: ChatConfig = field(default_factory=ChatConfig)


@dataclass
class TelegramSettings:
    """Telegram bot and chat configuration."""

    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: RegularsChats = field(default_factory=RegularsChats)
    substitutes: SubstitutesChats = field(default_factory=SubstitutesChats)
    management: ManagementChats = field(default_factory=ManagementChats)

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids


@dataclass
class TelegramAppSettings(AppSettings):
    """Combined settings for the Telegram+FastAPI topology."""

    telegram: TelegramSettings = field(default_factory=TelegramSettings)


def load_telegram_app_settings(
    base: AppSettings,
    config_path: Path = Path("config.toml"),
) -> TelegramAppSettings:
    """Load and validate Telegram settings, extending base AppSettings.

    Args:
        base: Pre-loaded AppSettings instance.
        config_path: Path to config.toml.

    Returns:
        TelegramAppSettings combining base and Telegram-specific config.

    Raises:
        SettingsValidationError: If required Telegram settings are missing.
    """
    if not config_path.exists():
        raise SettingsValidationError(
            f"No se encontró el archivo de configuración: '{config_path}'. "
            "Ejecuta 'pyball-telegram --bootstrap' para generar un config.toml de ejemplo."
        )
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    telegram_cfg = config.get("pyball", {}).get("telegram", {})
    regulars_cfg = telegram_cfg.get("regulars", {})
    substitutes_cfg = telegram_cfg.get("substitutes", {})
    management_cfg = telegram_cfg.get("management", {})

    telegram = TelegramSettings(
        bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
        admins_ids=_parse_admins_ids(
            _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
        ),
        regulars=RegularsChats(
            meetups=_load_chat_config(
                regulars_cfg.get("meetups", {}), "telegram.regulars.meetups"
            ),
            stats=_load_chat_config(regulars_cfg.get("stats", {}), "telegram.regulars.stats"),
        ),
        substitutes=SubstitutesChats(
            meetups=_load_chat_config(
                substitutes_cfg.get("meetups", {}), "telegram.substitutes.meetups"
            ),
        ),
        management=ManagementChats(
            activity=_load_chat_config(
                management_cfg.get("activity", {}), "telegram.management.activity"
            ),
        ),
    )

    missing = []
    if not telegram.bot_token:
        missing.append("telegram.bot_token")
    if not telegram.admins_ids:
        missing.append("telegram.admins_ids")
    if not telegram.regulars.meetups.chat_id:
        missing.append("telegram.regulars.meetups.chat_id")
    if not telegram.substitutes.meetups.chat_id:
        missing.append("telegram.substitutes.meetups.chat_id")

    if missing:
        raise SettingsValidationError(
            f"Faltan parámetros requeridos: {', '.join(missing)}. "
            "Ejecuta 'pyball-telegram --bootstrap' para generar un config.toml de ejemplo."
        )

    if not telegram.regulars.stats.chat_id:
        logger.warning(
            "telegram.regulars.stats no está configurado: no se publicarán "
            "estadísticas tras los partidos."
        )

    return TelegramAppSettings(
        pyball=base.pyball,
        paths=base.paths,
        telegram=telegram,
    )


def _load_chat_config(section: dict, env_path: str) -> ChatConfig:
    """Build a ChatConfig from a config sub-section plus PYBALL_* env overrides.

    Args:
        section: The parsed TOML table for this destination (may be empty).
        env_path: Dotted path used to derive env var names, e.g.
            "telegram.regulars.meetups" -> PYBALL_TELEGRAM_REGULARS_MEETUPS_CHAT_ID.
    """
    chat_id = _parse_chat_id(_get_env_override(env_path, "chat_id", section.get("chat_id", 0)))
    raw_thread = _get_env_override(env_path, "message_thread_id", section.get("message_thread_id"))
    return ChatConfig(chat_id=chat_id, message_thread_id=_parse_thread_id(raw_thread))


def _parse_chat_id(value) -> int:
    """Parse chat_id from config or env, handling empty strings."""
    if isinstance(value, str) and not value:
        return 0
    return int(value)


def _parse_thread_id(value) -> int | None:
    """Parse a forum topic id from config or env; empty/absent/zero becomes None."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return int(value) or None


def _parse_admins_ids(value) -> tuple[int, ...]:
    """Parse admins_ids from config or env override."""
    if isinstance(value, list):
        return tuple(int(x) for x in value)
    if isinstance(value, str):
        return tuple(int(x.strip()) for x in value.split(",") if x.strip())
    return ()


def _get_env_override(section: str, key: str, default):
    """Get environment variable override for a Telegram config value.

    Env var format: PYBALL_<SECTION>_<KEY> with dots replaced by underscores.
    Example: section='telegram.regulars.meetups', key='chat_id'
    -> PYBALL_TELEGRAM_REGULARS_MEETUPS_CHAT_ID
    """
    env_key = f"PYBALL_{section.upper().replace('.', '_')}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is None:
        return default
    return env_value
