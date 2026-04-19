"""Meetup models."""

from __future__ import annotations

import random as _random
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from pyball.domain.base import Entity, ValueObject
from pyball.domain.meetup.errors import InvalidMeetupIdError, PlayerNotInMeetupError
from pyball.domain.player.models import PlayerId


@dataclass(frozen=True)
class GoalEvent(ValueObject):
    """Value object representing a single goal event."""

    scorer_id: PlayerId
    assistant_id: PlayerId | None
    team: str
    timestamp: datetime


@dataclass(frozen=True)
class MatchResult(ValueObject):
    """Value object representing the final result of a match."""

    score_a: int
    score_b: int
    events: tuple[GoalEvent, ...]


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

    def create_random_teams(self) -> None:
        """Create two randomly-assigned teams from the players."""
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to create teams")

        players_copy = list(self.players)
        _random.shuffle(players_copy)

        mid = len(players_copy) // 2
        self.teams = [
            Team.create("A", players_copy[:mid]),
            Team.create("B", players_copy[mid:]),
        ]

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
