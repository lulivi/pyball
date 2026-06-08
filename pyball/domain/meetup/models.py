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
"""Meetup models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from uuid import UUID, uuid4

from pyball.domain.base import Entity, ValueObject
from pyball.domain.meetup.errors import InvalidMeetupIdError, PlayerNotInMeetupError
from pyball.domain.player.models import PlayerId


@dataclass
class Meetup(Entity["MeetupId"]):
    """Meetup entity - represents a football session."""

    id: MeetupId
    date: datetime
    location: str
    players: list[PlayerId] = field(default_factory=list)
    teams: list[Team] | None = None
    result: MatchResult | None = None

    @classmethod
    def create(cls, date: datetime, location: str) -> "Meetup":
        """Create a new meetup with the given date and location."""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        return cls(id=MeetupId.generate(), date=date, location=location.strip())

    def add_player(self, player_id: PlayerId) -> None:
        """Add a player to the meetup."""
        if player_id not in self.players:
            self.players.append(player_id)

    def remove_player(self, player_id: PlayerId) -> None:
        """Remove a player from the meetup."""
        if player_id not in self.players:
            raise PlayerNotInMeetupError(str(player_id.value))
        self.players.remove(player_id)

    def set_result(self, result: MatchResult) -> None:
        """Attach the match result. Requires teams to exist."""
        if self.teams is None:
            raise ValueError("Cannot set result without teams")
        self.result = result

    def is_closed(self) -> bool:
        """Return True if the match result has been recorded."""
        return self.result is not None

    def set_teams(self, teams: list[Team]) -> None:
        """Assign pre-computed teams to this meetup."""
        if len(teams) != 2:
            raise ValueError("Exactly two teams required")
        self.teams = teams

    def clear_teams(self) -> None:
        """Clear any assigned teams."""
        self.teams = None

    def set_location(self, location: str) -> None:
        """Set the meetup location."""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        self.location = location.strip()

    def set_date(self, date: datetime) -> None:
        """Set the meetup date."""
        self.date = date


@dataclass(frozen=True)
class GoalEvent(ValueObject):
    """Value object representing a single goal event."""

    scorer_id: PlayerId
    assistant_id: PlayerId | None
    team: str
    timestamp: time
    is_own_goal: bool = False


@dataclass(frozen=True)
class MatchResult(ValueObject):
    """Value object representing the final result of a match."""

    score_a: int
    score_b: int
    events: tuple[GoalEvent, ...]


@dataclass(frozen=True)
class Team(ValueObject):
    """Value object representing a team."""

    name: str
    players: tuple[PlayerId, ...]

    @classmethod
    def create(cls, name: str, players: list[PlayerId]) -> "Team":
        """Create a team with the given name and player list."""
        return cls(name=name, players=tuple(players))


@dataclass(frozen=True)
class MeetupId(ValueObject):
    """Value object for meetup identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "MeetupId":
        """Create a MeetupId from a string UUID."""
        try:
            return cls(UUID(value))
        except ValueError as e:
            raise InvalidMeetupIdError(value) from e

    @classmethod
    def generate(cls) -> "MeetupId":
        """Generate a new random MeetupId."""
        return cls(uuid4())
