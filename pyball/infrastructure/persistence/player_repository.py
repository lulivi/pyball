"""JSON file-based player repository."""

import json

from pathlib import Path
from uuid import UUID

from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class JsonPlayerRepository(PlayerRepository):
    """JSON file-based player repository."""

    def _read(self) -> dict:
        with open(self.file_path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({"players": []})

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()

    def save(self, player: Player) -> None:
        """Save a player to the repository."""
        data = self._read()
        players = data.get("players", [])
        for i, p in enumerate(players):
            if p["id"] == str(player.id.value):
                players[i] = {
                    "id": str(player.id.value),
                    "name": player.name,
                    "group": player.group,
                }
                break
        else:
            players.append(
                {"id": str(player.id.value), "name": player.name, "group": player.group}
            )
        self._write({"players": players})

    def find_by_id(self, player_id: PlayerId) -> Player | None:
        """Find a player by their ID."""
        data = self._read()
        for p in data.get("players", []):
            if p["id"] == str(player_id.value):
                return Player(
                    id=PlayerId(UUID(p["id"])), name=p["name"], group=p.get("group", "regular")
                )
        return None

    def find_by_name(self, name: str) -> Player | None:
        """Find a player by their name (case-insensitive)."""
        data = self._read()
        for p in data.get("players", []):
            if p["name"].lower() == name.lower():
                return Player(
                    id=PlayerId(UUID(p["id"])), name=p["name"], group=p.get("group", "regular")
                )
        return None

    def find_all(self) -> list[Player]:
        """Return all players."""
        data = self._read()
        return [
            Player(id=PlayerId(UUID(p["id"])), name=p["name"], group=p.get("group", "regular"))
            for p in data.get("players", [])
        ]

    def delete(self, player_id: PlayerId) -> None:
        """Delete a player by their ID."""
        data = self._read()
        players = [p for p in data.get("players", []) if p["id"] != str(player_id.value)]
        self._write({"players": players})
