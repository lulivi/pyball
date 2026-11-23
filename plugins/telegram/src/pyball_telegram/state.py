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

"""The plugin's own state in data/plugins/telegram/: tracked messages and linked users."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pyball_client.plugin import write_atomic

ChatType = Literal["regular", "substitute"]


@dataclass(frozen=True)
class TrackedMessage:
    """The Telegram message showing a meetup in one chat."""

    chat_id: int
    message_id: int
    thread_id: int | None = None


class MessageStore:
    """Maps each meetup date to the callup messages showing it, one per chat type.

    Keys are ``YYYY-MM-DDTHH:MM``: ``{"2026-04-15T20:00": {"regular": {...}}}``.
    """

    def __init__(self, path: Path) -> None:
        """Keep the store in ``path``, created on the first write."""
        self._path = path

    def save(self, date: datetime, chat: ChatType, message: TrackedMessage) -> None:
        """Track ``message`` as the one showing the meetup at ``date`` in ``chat``."""
        data = self._read()
        data.setdefault(_key(date), {})[chat] = {
            "chat_id": message.chat_id,
            "thread_id": message.thread_id,
            "message_id": message.message_id,
        }
        self._write(data)

    def get(self, date: datetime, chat: ChatType) -> TrackedMessage | None:
        """Return the message showing the meetup at ``date`` in ``chat``, if any."""
        entry = self._read().get(_key(date), {}).get(chat)
        if entry is None:
            return None
        return TrackedMessage(entry["chat_id"], entry["message_id"], entry.get("thread_id"))

    def delete(self, date: datetime, chat: ChatType) -> None:
        """Stop tracking the message of the meetup at ``date`` in ``chat``."""
        data = self._read()
        entry = data.get(_key(date), {})
        if chat in entry:
            del entry[chat]
            if not entry:
                del data[_key(date)]
            self._write(data)

    def rename_date(self, old: datetime, new: datetime) -> None:
        """Move the messages of a meetup whose date changed."""
        data = self._read()
        if _key(old) in data:
            data[_key(new)] = data.pop(_key(old))
            self._write(data)

    def _read(self) -> dict[str, Any]:
        return _read_json(self._path)

    def _write(self, data: dict[str, Any]) -> None:
        write_atomic(self._path, json.dumps(data, indent=2))


class LinkStore:
    """Links Telegram user ids to player ids: ``{"<telegram id>": "<player id>"}``."""

    def __init__(self, path: Path) -> None:
        """Keep the store in ``path``, created on the first write."""
        self._path = path

    def player_id(self, telegram_id: int) -> str | None:
        """Return the player linked to ``telegram_id``, if any."""
        found: str | None = _read_json(self._path).get(str(telegram_id))
        return found

    def telegram_id(self, player_id: str) -> int | None:
        """Return the Telegram user linked to ``player_id``, if any."""
        for telegram_id, linked in _read_json(self._path).items():
            if linked == player_id:
                return int(telegram_id)
        return None

    def link(self, telegram_id: int, player_id: str) -> None:
        """Link ``telegram_id`` to ``player_id``."""
        data = _read_json(self._path)
        data[str(telegram_id)] = player_id
        write_atomic(self._path, json.dumps(data, indent=2))

    def unlink(self, telegram_id: int) -> None:
        """Remove the link of ``telegram_id``."""
        data = _read_json(self._path)
        if data.pop(str(telegram_id), None) is not None:
            write_atomic(self._path, json.dumps(data, indent=2))


def _key(date: datetime) -> str:
    return date.isoformat(timespec="minutes")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data
