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
"""Telegram message tracking storage."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class MessageTracking:
    """Stores Telegram message tracking information."""

    chat_id: int
    message_id: int
    thread_id: str | int | None = None
    search_target: int | None = None


ChatType = Literal["regular", "substitute"]


class TelegramMessageStore:
    """Maps meetup dates to Telegram message IDs. DDD-compliant - infrastructure only."""

    def __init__(self, file_path: Path):
        """Initialize the store with the given file path."""
        self.file_path = file_path
        self._ensure_file_exists()

    def save_message(
        self, meetup_date: datetime, chat_type: ChatType, tracking: MessageTracking
    ) -> None:
        """Save message info for a meetup. chat_type is 'regular' or 'substitute'."""
        key = meetup_date.isoformat(timespec="minutes")  # e.g. "2026-04-15T20:00"
        data = self._read()
        if key not in data:
            data[key] = {}
        entry = {
            "chat_id": tracking.chat_id,
            "thread_id": tracking.thread_id,
            "message_id": tracking.message_id,
        }
        if tracking.search_target is not None:
            entry["search_target"] = tracking.search_target
        data[key][chat_type] = entry
        self._write(data)

    def get_message(self, meetup_date: datetime, chat_type: ChatType) -> MessageTracking | None:
        """Get message tracking for a meetup."""
        key = meetup_date.isoformat(timespec="minutes")  # e.g. "2026-04-15T20:00"
        data = self._read()
        if key not in data or chat_type not in data[key]:
            return None
        msg = data[key][chat_type]
        return MessageTracking(
            chat_id=msg["chat_id"],
            thread_id=msg.get("thread_id"),
            message_id=msg["message_id"],
            search_target=msg.get("search_target"),
        )

    def delete_message(self, meetup_date: datetime, chat_type: ChatType) -> None:
        """Delete message tracking."""
        key = meetup_date.isoformat(timespec="minutes")  # e.g. "2026-04-15T20:00"
        data = self._read()
        if key in data and chat_type in data[key]:
            del data[key][chat_type]
            if not data[key]:
                del data[key]
            self._write(data)

    def rename_date(self, old_date: datetime, new_date: datetime) -> None:
        """Re-key the messages entry from old_date to new_date."""
        old_key = old_date.isoformat(timespec="minutes")
        new_key = new_date.isoformat(timespec="minutes")
        data = self._read()
        if old_key in data:
            data[new_key] = data.pop(old_key)
            self._write(data)

    def _ensure_file_exists(self) -> None:
        """Ensure the storage file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        """Read data from the JSON file."""
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        """Write data to the JSON file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
