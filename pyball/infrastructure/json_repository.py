"""JSON file-based repository implementations."""

import json

from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.meetup.repository import MeetupRepository
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


class JsonMeetupRepository(MeetupRepository):
    """JSON file-based meetup repository."""

    def _get_file_path(self, meetup: Meetup) -> Path:
        return self.directory / f"{meetup.id.value}.json"

    def _read_file(self, file_path: Path) -> dict | None:
        if not file_path.exists():
            return None
        with open(file_path) as f:
            return json.load(f)

    def _dict_to_meetup(self, data: dict) -> Meetup:
        teams = None
        if data.get("teams"):
            teams = [
                Team.create(t["name"], [PlayerId(UUID(p)) for p in t["players"]])
                for t in data["teams"]
            ]
        return Meetup(
            id=MeetupId(UUID(data["id"])),
            date=datetime.fromisoformat(data["date"]),
            location=data.get("location", "Parque Central"),
            players=[PlayerId(UUID(p)) for p in data.get("players", [])],
            teams=teams,
        )

    def _write(self, meetup: Meetup) -> None:
        file_path = self._get_file_path(meetup)
        teams_data = None
        if meetup.teams:
            teams_data = [
                {"name": t.name, "players": [str(p.value) for p in t.players]}
                for t in meetup.teams
            ]
        data = {
            "id": str(meetup.id.value),
            "date": meetup.date.isoformat(),
            "location": meetup.location,
            "players": [str(p.value) for p in meetup.players],
            "teams": teams_data,
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, meetup: Meetup) -> None:
        """Save a meetup to the repository."""
        self._write(meetup)

    def find_by_id(self, meetup_id: MeetupId) -> Meetup | None:
        """Find a meetup by its ID."""
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data and data["id"] == str(meetup_id.value):
                return self._dict_to_meetup(data)
        return None

    def find_by_date(self, meetup_date: date) -> Meetup | None:
        """Find a meetup by its date."""
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data:
                meetup_date_from_data = datetime.fromisoformat(data["date"]).date()
                if meetup_date_from_data == meetup_date:
                    return self._dict_to_meetup(data)
        return None

    def find_all(self) -> list[Meetup]:
        """Return all meetups sorted by date."""
        meetups = []
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data:
                meetups.append(self._dict_to_meetup(data))
        return sorted(meetups, key=lambda m: m.date)

    def delete(self, meetup_id: MeetupId) -> None:
        """Delete a meetup by its ID."""
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data and data["id"] == str(meetup_id.value):
                file_path.unlink()
                return
