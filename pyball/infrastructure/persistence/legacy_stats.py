"""Legacy statistics loader for historical assist data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LegacyStats:
    """Read-only access to legacy aggregate statistics."""

    _data: dict[str, dict[str, dict[str, int]]]

    def get(self, player_id: str) -> dict[str, int]:
        """Return {goals, assists, matches} for player_id, or zeros if not found."""
        if player_id in self._data.get("players", {}):
            return self._data["players"][player_id]
        return {"goals": 0, "assists": 0, "matches": 0}

    def get_assists(self, player_id: str) -> int:
        """Return total assists for player_id."""
        return self.get(player_id).get("assists", 0)

    def get_goals(self, player_id: str) -> int:
        """Return total goals for player_id."""
        return self.get(player_id).get("goals", 0)

    def get_matches(self, player_id: str) -> int:
        """Return total matches for player_id."""
        return self.get(player_id).get("matches", 0)

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
