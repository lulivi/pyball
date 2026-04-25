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
"""Telegram ID to player ID mapping storage."""

import json
from pathlib import Path


class TelegramMappingStore:
    """Store telegram_id -> player_id mappings."""

    def __init__(self, file_path: Path):
        """Initialize the store with a file path."""
        self.file_path = file_path
        self._ensure_file_exists()

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

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
