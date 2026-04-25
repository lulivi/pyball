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

    _data: dict[str, dict[str, dict[str, Any]]]

    def get(self, player_id: str) -> dict[str, int]:
        """Return {goals, assists, matches} for player_id, or zeros if not found."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if not player_data:
            return {"goals": 0, "assists": 0, "matches": 0}
        # If using new granular format, compute totals
        if "goals_by_match" in player_data:
            goals = sum(e["count"] for e in player_data["goals_by_match"])
            assists = sum(e["count"] for e in player_data.get("assists_by_match", []))
            match_dates = set()
            for e in player_data.get("goals_by_match", []):
                match_dates.add(e["date"])
            for e in player_data.get("assists_by_match", []):
                match_dates.add(e["date"])
            return {"goals": goals, "assists": assists, "matches": len(match_dates)}
        # Legacy aggregate format
        return {
            "goals": player_data.get("goals", 0),
            "assists": player_data.get("assists", 0),
            "matches": player_data.get("matches", 0),
        }

    def get_assists(self, player_id: str) -> int:
        """Return total assists for player_id."""
        return self.get(player_id).get("assists", 0)

    def get_goals(self, player_id: str) -> int:
        """Return total goals for player_id."""
        return self.get(player_id).get("goals", 0)

    def get_matches(self, player_id: str) -> int:
        """Return total matches for player_id."""
        return self.get(player_id).get("matches", 0)

    def get_goals_since(self, player_id: str, since: datetime) -> int:
        """Return total goals since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "goals_by_match" not in player_data:
            return player_data.get("goals", 0)
        total = 0
        since_iso = since.isoformat()
        for entry in player_data["goals_by_match"]:
            if entry["date"] >= since_iso:
                total += entry["count"]
        return total

    def get_assists_since(self, player_id: str, since: datetime) -> int:
        """Return total assists since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "assists_by_match" not in player_data:
            return player_data.get("assists", 0)
        total = 0
        since_iso = since.isoformat()
        for entry in player_data.get("assists_by_match", []):
            if entry["date"] >= since_iso:
                total += entry["count"]
        return total

    def get_matches_since(self, player_id: str, since: datetime) -> int:
        """Return total matches since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "goals_by_match" not in player_data and "assists_by_match" not in player_data:
            return player_data.get("matches", 0)
        match_dates: set[str] = set()
        since_iso = since.isoformat()
        for entry in player_data.get("goals_by_match", []):
            if entry["date"] >= since_iso:
                match_dates.add(entry["date"])
        for entry in player_data.get("assists_by_match", []):
            if entry["date"] >= since_iso:
                match_dates.add(entry["date"])
        return len(match_dates)

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
