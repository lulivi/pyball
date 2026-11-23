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

"""Settings: the plugin API from the environment, the rest from the plugin's own
``[pyball.plugins.telegram]`` table in PyBall's config.toml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyball_client import plugin
from pyball_client.plugin import PluginError

NAME = "telegram"
"""The plugin's table and its folder under data/plugins/."""

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Chat:
    """A Telegram message destination: a chat and an optional forum topic."""

    chat_id: int = 0
    thread_id: int | None = None

    def __bool__(self) -> bool:
        """Return True when a chat is configured."""
        return bool(self.chat_id)


@dataclass(frozen=True)
class Config:  # pylint: disable=too-many-instance-attributes
    """Everything the plugin needs to run."""

    bot_token: str
    admins_ids: frozenset[int]
    regulars_meetups: Chat
    substitutes_meetups: Chat
    regulars_stats: Chat = field(default_factory=Chat)
    data_dir: Path = field(default_factory=lambda: plugin.data_dir(NAME))

    @property
    def messages_file(self) -> Path:
        """Return the file tracking which message shows each meetup."""
        return self.data_dir / "messages.json"

    @property
    def mapping_file(self) -> Path:
        """Return the file linking Telegram users to players."""
        return self.data_dir / "telegram-uuid.json"

    @property
    def event_id_file(self) -> Path:
        """Return the file holding the id of the last event handled."""
        return self.data_dir / "last_event_id"

    def is_admin(self, user_id: int) -> bool:
        """Return whether ``user_id`` may run admin commands."""
        return user_id in self.admins_ids


def load(config_path: Path) -> Config:
    """Read the plugin's table in ``config_path``; raise PluginError when it is incomplete."""
    return from_table(plugin.table(config_path, NAME))


def from_table(t: dict[str, Any]) -> Config:
    """Build the config from the plugin's table."""
    regulars = _section(t, "regulars")
    substitutes = _section(t, "substitutes")
    config = Config(
        bot_token=str(t.get("bot_token", "")).strip(),
        admins_ids=_admins(t.get("admins_ids", [])),
        regulars_meetups=_chat(regulars, "regulars", "meetups"),
        substitutes_meetups=_chat(substitutes, "substitutes", "meetups"),
        regulars_stats=_chat(regulars, "regulars", "stats"),
    )
    missing = [
        key
        for key, given in (
            ("bot_token", config.bot_token),
            ("admins_ids", config.admins_ids),
            ("regulars.meetups.chat_id", config.regulars_meetups),
            ("substitutes.meetups.chat_id", config.substitutes_meetups),
        )
        if not given
    ]
    if missing:
        raise PluginError(f"plugins.{NAME} is missing {', '.join(missing)}")
    if not config.regulars_stats:
        logger.warning("plugins.%s.regulars.stats is not set: no stats after matches", NAME)
    return config


def _section(t: dict[str, Any], key: str, path: str | None = None) -> dict[str, Any]:
    value = t.get(key, {})
    if not isinstance(value, dict):
        raise PluginError(f"plugins.{NAME}.{path or key} must be a table")
    return value


def _chat(parent: dict[str, Any], parent_key: str, key: str) -> Chat:
    path = f"{parent_key}.{key}"
    section = _section(parent, key, path)
    try:
        chat_id = int(section.get("chat_id") or 0)
        thread = section.get("message_thread_id")
        thread_id = int(str(thread)) if str(thread or "").strip() else None
    except (TypeError, ValueError) as exc:
        raise PluginError(
            f"plugins.{NAME}.{path}.chat_id and message_thread_id must be numbers"
        ) from exc
    return Chat(chat_id, thread_id or None)


def _admins(value: Any) -> frozenset[int]:
    if not isinstance(value, list):
        raise PluginError(f"plugins.{NAME}.admins_ids must be a list of Telegram user ids")
    try:
        return frozenset(int(v) for v in value)
    except (TypeError, ValueError) as exc:
        raise PluginError(f"plugins.{NAME}.admins_ids must hold numbers") from exc
