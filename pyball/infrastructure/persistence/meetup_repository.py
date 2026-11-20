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
"""JSON file-based meetup repository."""

import json
from datetime import datetime, time
from pathlib import Path
from uuid import UUID

from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, MeetupId, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class JsonMeetupRepository(MeetupRepository):
    """JSON file-based meetup repository."""

    def __init__(self, directory: Path, default_capacity: int):
        """Initialize the repository with a storage directory.

        ``default_capacity`` is the capacity of a stored meetup that has none yet.
        """
        self.directory = directory
        self.default_capacity = default_capacity
        self.directory.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, meetup: Meetup) -> Path:
        return self.directory / f"{meetup.date.isoformat(timespec='minutes')}.json"

    def _read_file(self, file_path: Path) -> dict | None:
        if not file_path.exists():
            return None
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    def _dict_to_meetup(self, data: dict) -> Meetup:
        teams = None
        if data.get("teams"):
            teams = [
                Team.create(
                    t["name"],
                    [PlayerId(UUID(p)) for p in t["players"]],
                    goalkeeper=PlayerId(UUID(t["goalkeeper"])) if t.get("goalkeeper") else None,
                )
                for t in data["teams"]
            ]
        teams_by_name = {t.name: t for t in teams} if teams else {}
        matches = [
            Match(
                teams_playing=(
                    teams_by_name[m["teams_playing"][0]],
                    teams_by_name[m["teams_playing"][1]],
                ),
                result=_dict_to_result(m["result"]) if m.get("result") else None,
            )
            for m in data.get("matches", [])
        ]
        return Meetup(
            id=MeetupId(UUID(data["id"])),
            date=datetime.fromisoformat(data["date"]),
            location=data.get("location", "Parque Central"),
            players=[PlayerId(UUID(p)) for p in data.get("players", [])],
            teams=teams,
            matches=matches,
            closed=data.get("closed", False),
            capacity=data.get("capacity", self.default_capacity),
            substitute_search=data.get("substitute_search", False),
        )

    def _write(self, meetup: Meetup) -> None:
        file_path = self._get_file_path(meetup)
        teams_data = None
        if meetup.teams:
            teams_data = [
                {
                    "name": t.name,
                    "players": [str(p.value) for p in t.players],
                    "goalkeeper": str(t.goalkeeper.value) if t.goalkeeper else None,
                }
                for t in meetup.teams
            ]
        matches_data = [
            {
                "teams_playing": [m.teams_playing[0].name, m.teams_playing[1].name],
                "result": _result_to_dict(m.result) if m.result else None,
            }
            for m in meetup.matches
        ]
        data = {
            "id": str(meetup.id.value),
            "date": meetup.date.isoformat(),
            "location": meetup.location,
            "players": [str(p.value) for p in meetup.players],
            "teams": teams_data,
            "matches": matches_data,
            "closed": meetup.closed,
            "capacity": meetup.capacity,
            "substitute_search": meetup.substitute_search,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

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

    def find_by_datetime(self, meetup_date: datetime) -> Meetup | None:
        """Find a meetup by its datetime."""
        file_path = self.directory / f"{meetup_date.isoformat(timespec='minutes')}.json"
        data = self._read_file(file_path)
        return self._dict_to_meetup(data) if data else None

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

    def delete_by_datetime(self, meetup_date: datetime) -> None:
        """Delete the meetup file for the given datetime, if it exists."""
        file_path = self.directory / f"{meetup_date.isoformat(timespec='minutes')}.json"
        file_path.unlink(missing_ok=True)


def _dict_to_result(r: dict) -> MatchResult:
    """Build a MatchResult from its JSON dict representation."""
    events = tuple(
        GoalEvent(
            scorer_id=PlayerId(UUID(e["scorer_id"])),
            assistant_id=(PlayerId(UUID(e["assistant_id"])) if e.get("assistant_id") else None),
            team=e["team"],
            timestamp=time.fromisoformat(e["timestamp"]),
            is_own_goal=e.get("is_own_goal", False),
        )
        for e in r.get("events", [])
    )
    return MatchResult(score_a=r["score_a"], score_b=r["score_b"], events=events)


def _result_to_dict(result: MatchResult) -> dict:
    """Serialize a MatchResult to its JSON dict representation."""
    return {
        "score_a": result.score_a,
        "score_b": result.score_b,
        "events": [
            {
                "scorer_id": str(e.scorer_id.value),
                "assistant_id": str(e.assistant_id.value) if e.assistant_id else None,
                "team": e.team,
                "timestamp": e.timestamp.isoformat(),
                "is_own_goal": e.is_own_goal,
            }
            for e in result.events
        ],
    }
