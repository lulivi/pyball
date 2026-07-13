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
"""JSON file-based player repository."""

import json
from pathlib import Path
from uuid import UUID

from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class JsonPlayerRepository(PlayerRepository):
    """JSON file-based player repository."""

    def _read(self) -> dict:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({"players": []})

    def __init__(self, file_path: Path):
        """Initialize the repository with a file path."""
        self.file_path = file_path
        self._ensure_file_exists()

    def save(self, player: Player) -> None:
        """Save a player to the repository."""
        data = self._read()
        players = data.get("players", [])
        entry = {
            "id": str(player.id.value),
            "name": player.name,
            "group": player.group,
            "position": player.position,
        }
        for i, p in enumerate(players):
            if p["id"] == str(player.id.value):
                players[i] = entry
                break
        else:
            players.append(entry)
        self._write({"players": players})

    def find_by_id(self, player_id: PlayerId) -> Player | None:
        """Find a player by their ID."""
        data = self._read()
        for p in data.get("players", []):
            if p["id"] == str(player_id.value):
                return _player_from_dict(p)
        return None

    def find_by_name(self, name: str) -> Player | None:
        """Find a player by their name (case-insensitive)."""
        data = self._read()
        for p in data.get("players", []):
            if p["name"].lower() == name.lower():
                return _player_from_dict(p)
        return None

    def find_all(self) -> list[Player]:
        """Return all players."""
        data = self._read()
        return [_player_from_dict(p) for p in data.get("players", [])]

    def delete(self, player_id: PlayerId) -> None:
        """Delete a player by their ID."""
        data = self._read()
        players = [p for p in data.get("players", []) if p["id"] != str(player_id.value)]
        self._write({"players": players})


def _player_from_dict(p: dict) -> Player:
    """Build a Player from its JSON dict representation."""
    return Player(
        id=PlayerId(UUID(p["id"])),
        name=p["name"],
        group=p.get("group", "regular"),
        position=p.get("position"),
    )
