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

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pyball.settings import AppSettings, SettingsValidationError


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
            "Ejecuta 'pyball-tg --bootstrap' para generar un config.toml de ejemplo."
        )
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    telegram_cfg = config.get("pyball", {}).get("telegram", {})
    regulars_cfg = telegram_cfg.get("regulars", {})
    substitutes_cfg = telegram_cfg.get("substitutes", {})
    management_cfg = telegram_cfg.get("management", {})

    raw_meetups_thread = _get_env_override(
        "telegram.regulars", "meetups_thread_id", regulars_cfg.get("meetups_thread_id")
    )
    raw_stats_thread = _get_env_override(
        "telegram.regulars", "stats_thread_id", regulars_cfg.get("stats_thread_id")
    )
    raw_management_chat = _get_env_override(
        "telegram.management", "chat_id", management_cfg.get("chat_id")
    )

    regulars = RegularsChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override("telegram.regulars", "chat_id", regulars_cfg.get("chat_id", 0))
        ),
        meetups_thread_id=raw_meetups_thread if raw_meetups_thread is not None else "",
        stats_thread_id=raw_stats_thread if raw_stats_thread is not None else "",
    )
    substitutes = TelegramChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override("telegram.substitutes", "chat_id", substitutes_cfg.get("chat_id", 0))
        ),
    )
    management = ManagementChatSettings(
        chat_id=_parse_chat_id(raw_management_chat if raw_management_chat is not None else 0),
    )
    telegram = TelegramSettings(
        bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
        admins_ids=_parse_admins_ids(
            _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
        ),
        regulars=regulars,
        substitutes=substitutes,
        management=management,
    )

    missing = []
    if not telegram.bot_token:
        missing.append("telegram.bot_token")
    if not telegram.admins_ids:
        missing.append("telegram.admins_ids")
    if not telegram.regulars.chat_id:
        missing.append("telegram.regulars.chat_id")
    if not telegram.substitutes.chat_id:
        missing.append("telegram.substitutes.chat_id")
    if raw_meetups_thread is None:
        missing.append("telegram.regulars.meetups_thread_id")
    if raw_stats_thread is None:
        missing.append("telegram.regulars.stats_thread_id")
    if raw_management_chat is None:
        missing.append("telegram.management.chat_id")

    if missing:
        raise SettingsValidationError(
            f"Faltan parámetros requeridos: {', '.join(missing)}. "
            "Ejecuta 'pyball-tg --bootstrap' para generar un config.toml de ejemplo."
        )

    return TelegramAppSettings(
        pyball=base.pyball,
        paths=base.paths,
        telegram=telegram,
    )


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
    """Get environment variable override for Telegram config value.

    Env var format: PYBALL_<SECTION>_<KEY> with dots replaced by underscores.
    Example: section='telegram.regulars', key='chat_id' -> PYBALL_TELEGRAM_REGULARS_CHAT_ID
    """
    env_key = f"PYBALL_{section.upper().replace('.', '_')}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is None:
        return default
    return env_value
