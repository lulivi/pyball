"""Meetup models."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pyball.domain.base import Entity, ValueObject
from pyball.domain.meetup.errors import PlayerNotInMeetupError
from pyball.domain.player.models import PlayerId


@dataclass(frozen=True)
class MeetupId(ValueObject):
    """Value object for meetup identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "MeetupId":
        return cls(UUID(value))

    @classmethod
    def generate(cls) -> "MeetupId":
        return cls(UUID())


@dataclass(frozen=True)
class Team(ValueObject):
    """Value object representing a team."""

    name: str
    players: tuple[PlayerId, ...]

    @classmethod
    def create(cls, name: str, players: list[PlayerId]) -> "Team":
        return cls(name=name, players=tuple(players))


@dataclass
class Meetup(Entity):
    """Meetup entity - represents a football session."""

    id: MeetupId
    date: datetime
    regulars: list[PlayerId] = field(default_factory=list)
    substitutes: list[PlayerId] = field(default_factory=list)
    teams: list[Team] | None = None

    @classmethod
    def create(cls, date: datetime) -> "Meetup":
        return cls(id=MeetupId.generate(), date=date)

    def add_regular(self, player_id: PlayerId) -> None:
        if player_id in self.substitutes:
            self.substitutes.remove(player_id)
        if player_id not in self.regulars:
            self.regulars.append(player_id)

    def add_substitute(self, player_id: PlayerId) -> None:
        if player_id in self.regulars:
            self.regulars.remove(player_id)
        if player_id not in self.substitutes:
            self.substitutes.append(player_id)

    def remove_player(self, player_id: PlayerId) -> None:
        if player_id in self.regulars:
            self.regulars.remove(player_id)
        elif player_id in self.substitutes:
            self.substitutes.remove(player_id)
        else:
            raise PlayerNotInMeetupError(str(player_id.value))

    def create_balanced_teams(self, random_generator) -> None:
        if len(self.regulars) < 2:
            raise ValueError("Need at least 2 regulars to create teams")

        all_players = list(self.regulars)
        if len(all_players) % 2 != 0 and self.substitutes:
            all_players.append(self.substitutes[0])

        random_generator.shuffle(all_players)
        mid = len(all_players) // 2
        self.teams = [
            Team.create("Team A", all_players[:mid]),
            Team.create("Team B", all_players[mid:]),
        ]
