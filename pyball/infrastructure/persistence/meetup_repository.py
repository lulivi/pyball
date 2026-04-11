"""JSON file-based meetup repository."""

import json
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


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