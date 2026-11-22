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
from pyball.domain.meetup.errors import (
    InvalidCapacityError,
    InvalidMeetupIdError,
    MeetupFullError,
    PlayerNotInMeetupError,
    SignupClosedError,
)
from pyball.domain.player.models import PlayerId


@dataclass
class Meetup(Entity["MeetupId"]):  # pylint: disable=too-many-instance-attributes
    """Meetup entity - represents a football session."""

    id: MeetupId
    date: datetime
    location: str
    players: list[PlayerId] = field(default_factory=list)
    teams: list[Team] | None = None
    matches: list[Match] = field(default_factory=list)
    closed: bool = False
    capacity: int = 10
    substitute_search: bool = False

    @classmethod
    def create(cls, date: datetime, location: str, capacity: int = 10) -> "Meetup":
        """Create a new meetup with the given date, location and capacity."""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        _check_capacity(capacity)
        return cls(id=MeetupId.generate(), date=date, location=location.strip(), capacity=capacity)

    def add_player(self, player_id: PlayerId) -> None:
        """Add a player to the meetup; reaching capacity closes the substitute search."""
        if player_id not in self.players:
            self.players.append(player_id)
        self._close_search_if_full()

    def remove_player(self, player_id: PlayerId, default_capacity: int) -> None:
        """Remove a player from the meetup.

        During a substitute search for more than the club's ``default_capacity``, a roster
        that falls back to the default or below returns the capacity to the default, which
        closes the search when the roster sits exactly on it.
        """
        if player_id not in self.players:
            raise PlayerNotInMeetupError(str(player_id.value))
        self.players.remove(player_id)
        self._fall_back_to_default_capacity(default_capacity)

    def replace_players(self, player_ids: list[PlayerId], default_capacity: int) -> None:
        """Replace the whole roster, under the same capacity rules as joins and leaves."""
        self.players = list(dict.fromkeys(player_ids))
        self._fall_back_to_default_capacity(default_capacity)
        self._close_search_if_full()

    def set_capacity(self, capacity: int) -> None:
        """Set how many players the meetup plays with; reaching it closes the search."""
        _check_capacity(capacity)
        self._require_signup_open()
        self.capacity = capacity
        self._close_search_if_full()

    def open_substitute_search(self) -> None:
        """Start looking for substitutes until the roster reaches the capacity."""
        self._require_signup_open()
        if len(self.players) >= self.capacity:
            raise MeetupFullError(
                f"The roster already has {len(self.players)} of {self.capacity} players."
            )
        self.substitute_search = True

    def close_substitute_search(self) -> None:
        """Stop looking for substitutes."""
        self.substitute_search = False

    def set_teams(self, teams: list[Team]) -> None:
        """Assign pre-computed teams to this meetup. Accepts 2 (classic) or 3 (triangular).

        Teams close signup, and with it any substitute search.
        """
        if len(teams) not in (2, 3):
            raise ValueError("Two or three teams required")
        self.teams = teams
        self.substitute_search = False

    def clear_teams(self) -> None:
        """Clear any assigned teams, and any matches/closed state tied to them."""
        self.teams = None
        self.matches = []
        self.closed = False

    def has_recorded_results(self) -> bool:
        """Return True once any match in this meetup has a recorded result."""
        return any(match.result is not None for match in self.matches)

    def add_match(self, match: "Match") -> None:
        """Append a new pending (or already-resolved) match to this meetup."""
        self.matches.append(match)

    def current_match(self) -> "Match | None":
        """Return the pending match (no result yet), or None if none is pending."""
        if self.matches and self.matches[-1].result is None:
            return self.matches[-1]
        return None

    def record_result(self, result: "MatchResult") -> None:
        """Attach a result to the current pending match."""
        current = self.current_match()
        if current is None:
            raise ValueError("No pending match to record a result for")
        current.result = result

    def close(self) -> None:
        """Mark the meetup as closed. No further matches can be recorded."""
        self.closed = True

    def is_closed(self) -> bool:
        """Return True if the meetup has been closed."""
        return self.closed

    def is_signup_open(self) -> bool:
        """Return True if players may still join or leave (no teams assigned yet)."""
        return self.teams is None

    def set_location(self, location: str) -> None:
        """Set the meetup location."""
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        self.location = location.strip()

    def set_date(self, date: datetime) -> None:
        """Set the meetup date."""
        self.date = date

    def _require_signup_open(self) -> None:
        if not self.is_signup_open():
            raise SignupClosedError("The meetup already has teams.")

    def _fall_back_to_default_capacity(self, default_capacity: int) -> None:
        if self.substitute_search and len(self.players) <= default_capacity < self.capacity:
            self.capacity = default_capacity
            self._close_search_if_full()

    def _close_search_if_full(self) -> None:
        if len(self.players) >= self.capacity:
            self.substitute_search = False


@dataclass
class Match:
    """A single 2-team match within a meetup (one match, or one of several in a triangular)."""

    teams_playing: tuple["Team", "Team"]
    result: "MatchResult | None" = None


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

    def winner_index(self) -> int | None:
        """Return the winning team's index in teams_playing (0 or 1), or None on a draw."""
        if self.score_a == self.score_b:
            return None
        return 0 if self.score_a > self.score_b else 1


@dataclass(frozen=True)
class Team(ValueObject):
    """Value object representing a team."""

    name: str
    players: tuple[PlayerId, ...]
    goalkeeper: PlayerId | None = None

    def __post_init__(self) -> None:
        """Validate that a set goalkeeper is one of the team's players."""
        if self.goalkeeper is not None and self.goalkeeper not in self.players:
            raise ValueError("Team goalkeeper must be one of the team's players")

    @classmethod
    def create(
        cls, name: str, players: list[PlayerId], goalkeeper: PlayerId | None = None
    ) -> "Team":
        """Create a team with the given name, player list, and optional goalkeeper."""
        return cls(name=name, players=tuple(players), goalkeeper=goalkeeper)


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


def _check_capacity(capacity: int) -> None:
    if capacity < 2:
        raise InvalidCapacityError(f"Capacity must be at least 2, got {capacity}.")
