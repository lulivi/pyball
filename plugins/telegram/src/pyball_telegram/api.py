"""The telegram plugin's calls to PyBall's plugin API, and the fields it reads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pyball_client import Endpoint
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """The club settings messages are displayed with."""

    display_date_format: str
    locale: str


class Player(BaseModel):
    """A player."""

    id: str
    name: str
    group: str


class Team(BaseModel):
    """One team of a meetup, in the club color of its position."""

    name: str
    color: str
    emoji: str
    players: list[str]


class Match(BaseModel):
    """One match: the names of the two teams playing and its score, null while played."""

    teams: list[str]
    score: list[int] | None


class Meetup(BaseModel):
    """A meetup, its roster as player ids."""

    id: str
    date: datetime
    location: str
    capacity: int
    substitute_search: bool
    players: list[str]
    teams: list[Team] | None
    matches: list[Match]
    closed: bool

    def signup_open(self) -> bool:
        """Return whether players may still join or leave: no teams yet."""
        return self.teams is None


class Summary(BaseModel):
    """The result summary of a closed meetup."""

    text: str


class Event(BaseModel):
    """Something that happened to a meetup, with the meetup right after."""

    id: int
    kind: str = Field(alias="type")
    meetup: Meetup
    previous_date: datetime | None = None


SETTINGS: Endpoint[Settings] = Endpoint("GET", "/settings", Settings)
PLAYERS: Endpoint[list[Player]] = Endpoint("GET", "/players", list[Player])
ACTIVE: Endpoint[Meetup] = Endpoint("GET", "/meetups/active", Meetup)
MEETUPS: Endpoint[list[Meetup]] = Endpoint("GET", "/meetups", list[Meetup], query=("date",))
SUMMARY: Endpoint[Summary] = Endpoint("GET", "/meetups/{meetup_id}/summary", Summary)
STATS: Endpoint[bytes] = Endpoint("GET", "/stats.png", bytes, query=("scope",))
JOIN: Endpoint[Meetup] = Endpoint("PUT", "/meetups/{meetup_id}/players/{player_id}", Meetup)
LEAVE: Endpoint[Meetup] = Endpoint("DELETE", "/meetups/{meetup_id}/players/{player_id}", Meetup)
EVENTS: Endpoint[Event] = Endpoint("GET", "/events", Event)

ENDPOINTS: list[Endpoint[Any]] = [
    SETTINGS,
    PLAYERS,
    ACTIVE,
    MEETUPS,
    SUMMARY,
    STATS,
    JOIN,
    LEAVE,
    EVENTS,
]
"""Every call the plugin makes; tests/test_contract.py checks them against the schema."""
