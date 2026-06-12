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
"""Serialisation of domain objects into HTTP response dicts."""
from __future__ import annotations

import functools
import locale
from typing import TYPE_CHECKING

from fastapi import HTTPException

from pyball.domain.meetup.errors import MeetupNotFoundError

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.domain.meetup.models import Meetup


def build_active_match_response(container: Container) -> dict:
    """Build the response dict for GET /api/match/active, or raise 404."""
    try:
        meetup = container.get_active_meetup().execute(require_teams=True)
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No active match found") from exc
    assert meetup.teams is not None  # guaranteed by require_teams=True

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text

    team_a = sorted_names(meetup.teams[0].players, player_names)
    team_b = sorted_names(meetup.teams[1].players, player_names)

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "teamA": team_a,
        "teamB": team_b,
        "nameA": colors[0].capitalize(),
        "nameB": colors[1].capitalize(),
        "colorA": hex_bg[0],
        "colorB": hex_bg[1],
        "colorTextA": hex_text[0],
        "colorTextB": hex_text[1],
    }


def build_meetup_active_response(container: Container) -> dict:
    """Build the response for GET /api/meetup/active, or raise 404.

    Returns the most recent unfinished meetup regardless of whether teams exist.
    players and teamA/teamB names are sorted with locale.strcoll.
    """
    try:
        meetup = container.get_active_meetup().execute()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No active meetup found") from exc

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}

    _sort = functools.cmp_to_key(locale.strcoll)

    players = sorted(
        [
            {"id": str(pid.value), "name": player_names.get(str(pid.value), "(desconocido)")}
            for pid in meetup.players
        ],
        key=lambda p: _sort(p["name"]),
    )

    if meetup.teams is None:
        return {"date": meetup.date.strftime("%Y-%m-%dT%H:%M"), "players": players, "teams": None}

    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text
    emojis = container.team_emojis

    team_a = sorted_names(meetup.teams[0].players, player_names)
    team_b = sorted_names(meetup.teams[1].players, player_names)

    match_url = container.match_link_builder().build()

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "players": players,
        "teams": {
            "teamA": team_a,
            "teamB": team_b,
            "nameA": colors[0].capitalize(),
            "nameB": colors[1].capitalize(),
            "emojiA": emojis[0],
            "emojiB": emojis[1],
            "colorA": hex_bg[0],
            "colorB": hex_bg[1],
            "colorTextA": hex_text[0],
            "colorTextB": hex_text[1],
            "matchUrl": match_url,
        },
    }


def build_match_events_response(container: Container, meetup: Meetup) -> dict:
    """Serialise a closed meetup's events and team data into a response dict."""
    assert meetup.teams is not None
    assert meetup.result is not None

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text

    team_a = sorted_names(meetup.teams[0].players, player_names)
    team_b = sorted_names(meetup.teams[1].players, player_names)

    events = [
        {
            "scorer": player_names.get(str(ev.scorer_id.value), "(desconocido)"),
            "assistant": player_names.get(str(ev.assistant_id.value), "(desconocido)")
            if ev.assistant_id
            else None,
            "team": ev.team,
            "timestamp": ev.timestamp.strftime("%H:%M"),
            "is_own_goal": ev.is_own_goal,
        }
        for ev in reversed(meetup.result.events)
    ]

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "nameA": colors[0].capitalize(),
        "nameB": colors[1].capitalize(),
        "teamA": team_a,
        "teamB": team_b,
        "colorA": hex_bg[0],
        "colorB": hex_bg[1],
        "colorTextA": hex_text[0],
        "colorTextB": hex_text[1],
        "events": events,
    }


def sorted_names(player_ids, player_names: dict[str, str]) -> list[str]:
    """Return locale-sorted display names for a list of player IDs."""
    _sort = functools.cmp_to_key(locale.strcoll)
    return sorted(
        [player_names.get(str(pid.value), "(desconocido)") for pid in player_ids],
        key=_sort,
    )


def serialise_callup_match(match) -> dict:
    """Serialise a single callup match result to a JSON-compatible dict."""
    if match.player_id:
        return {
            "raw": match.raw,
            "player_id": match.player_id,
            "name": match.name,
            "confidence": match.confidence,
            "candidates": [],
        }
    return {
        "raw": match.raw,
        "player_id": None,
        "name": None,
        "confidence": match.confidence,
        "candidates": [
            {"player_id": c.player_id, "name": c.name, "confidence": c.confidence}
            for c in match.candidates
        ],
    }
