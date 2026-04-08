import json

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class MessageTracking:
    chat_id: int
    thread_id: str | int | None
    message_id: int


ChatType = Literal["main", "subs"]


class TelegramMessageStore:
    """Maps meetup dates to Telegram message IDs. DDD-compliant - infrastructure only."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        with open(self.file_path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_message(
        self, meetup_date: str, chat_type: ChatType, tracking: MessageTracking
    ) -> None:
        """Save message info for a meetup. chat_type is 'main' or 'subs'."""
        data = self._read()
        if meetup_date not in data:
            data[meetup_date] = {}
        data[meetup_date][chat_type] = {
            "chat_id": tracking.chat_id,
            "thread_id": tracking.thread_id,
            "message_id": tracking.message_id,
        }
        self._write(data)

    def get_message(self, meetup_date: str, chat_type: ChatType) -> MessageTracking | None:
        """Get message tracking for a meetup."""
        data = self._read()
        if meetup_date not in data or chat_type not in data[meetup_date]:
            return None
        msg = data[meetup_date][chat_type]
        return MessageTracking(
            chat_id=msg["chat_id"],
            thread_id=msg.get("thread_id"),
            message_id=msg["message_id"],
        )

    def delete_message(self, meetup_date: str, chat_type: ChatType) -> None:
        """Delete message tracking."""
        data = self._read()
        if meetup_date in data and chat_type in data[meetup_date]:
            del data[meetup_date][chat_type]
            if not data[meetup_date]:
                del data[meetup_date]
            self._write(data)
