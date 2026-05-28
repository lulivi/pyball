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
"""Legacy statistics loader for historical assist data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class LegacyStats:
    """Read-only access to legacy aggregate statistics."""

    _data: dict[str, Any]

    def get_assists(self, player_id: str, since: datetime | None = None) -> int:
        """Return total assists for player_id, optionally filtered to on-or-after since."""
        entries = self._data.get("players", {}).get(player_id, {}).get("assists_by_match", [])
        if since is None:
            return sum(e["count"] for e in entries)
        return sum(e["count"] for e in entries if datetime.fromisoformat(e["date"]) >= since)

    def get_assists_for_match(self, player_id: str, match_date: datetime) -> int:
        """Return assists for player_id in the match at match_date, or 0 if not found."""
        entries = self._data.get("players", {}).get(player_id, {}).get("assists_by_match", [])
        for entry in entries:
            if datetime.fromisoformat(entry["date"]) == match_date:
                return entry["count"]
        return 0

    def all_players(self) -> list[str]:
        """Return list of all player IDs in legacy stats."""
        return list(self._data.get("players", {}).keys())

    @classmethod
    def from_file(cls, path: str) -> LegacyStats:
        """Load legacy stats from a JSON file."""
        if not Path(path).exists():
            return cls({"players": {}})
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)
