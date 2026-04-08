"""Telegram ID to player ID mapping storage."""

import json

from pathlib import Path


class TelegramMappingStore:
    """Store telegram_id -> player_id mappings."""

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

    def get_player_id(self, telegram_id: int) -> str | None:
        """Get player_id for a telegram_id."""
        data = self._read()
        return data.get(str(telegram_id))

    def set_player_id(self, telegram_id: int, player_id: str) -> None:
        """Set player_id for a telegram_id."""
        data = self._read()
        data[str(telegram_id)] = player_id
        self._write(data)

    def delete_player_id(self, telegram_id: int) -> None:
        """Delete mapping for a telegram_id."""
        data = self._read()
        if str(telegram_id) in data:
            del data[str(telegram_id)]
            self._write(data)
