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
"""The /api/v1 contract: the shapes plugins read, shared by responses and events."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player


class PlayerOut(BaseModel):
    """A player."""

    id: str
    name: str
    group: str
    position: str | None


class TeamOut(BaseModel):
    """One team of a meetup: its positional name, its club color, its players and goalkeeper."""

    name: str
    color: str
    emoji: str
    players: list[str]
    goalkeeper: str | None


class MatchOut(BaseModel):
    """One match between two of the meetup's teams; score is null while it is played."""

    teams: list[str]
    score: list[int] | None


class MeetupOut(BaseModel):
    """A meetup: its roster as player ids, its capacity and its substitute search."""

    id: str
    date: datetime
    location: str
    capacity: int
    substitute_search: bool
    players: list[str]
    teams: list[TeamOut] | None
    matches: list[MatchOut]
    closed: bool


class SummaryOut(BaseModel):
    """The result summary of a closed meetup, as plain text with *bold* spans."""

    text: str


class SettingsOut(BaseModel):
    """The club settings a plugin displays with: its date format and locale."""

    display_date_format: str
    locale: str


class ErrorOut(BaseModel):
    """An error the core raised itself: why it refused, in ``detail``."""

    detail: str


class EventOut(BaseModel):
    """Something that happened to a meetup, with the meetup as it was right after."""

    id: int
    type: str
    occurred_at: datetime
    meetup: MeetupOut
    player: PlayerOut | None = None
    is_substitute: bool | None = None
    previous_date: datetime | None = None


def meetup_out(
    meetup: Meetup, team_colors: Sequence[str], team_emojis: Sequence[str]
) -> MeetupOut:
    """Build the v1 shape of a meetup; its i-th team wears the club's i-th color."""
    return MeetupOut(
        id=str(meetup.id.value),
        date=meetup.date,
        location=meetup.location,
        capacity=meetup.capacity,
        substitute_search=meetup.substitute_search,
        players=[str(p.value) for p in meetup.players],
        teams=(
            [
                TeamOut(
                    name=t.name,
                    color=team_colors[i],
                    emoji=team_emojis[i],
                    players=[str(p.value) for p in t.players],
                    goalkeeper=str(t.goalkeeper.value) if t.goalkeeper else None,
                )
                for i, t in enumerate(meetup.teams)
            ]
            if meetup.teams is not None
            else None
        ),
        matches=[
            MatchOut(
                teams=[m.teams_playing[0].name, m.teams_playing[1].name],
                score=[m.result.score_a, m.result.score_b] if m.result else None,
            )
            for m in meetup.matches
        ],
        closed=meetup.closed,
    )


def player_out(player: Player) -> PlayerOut:
    """Build the v1 shape of a player."""
    return PlayerOut(
        id=str(player.id.value), name=player.name, group=player.group, position=player.position
    )
