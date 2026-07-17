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
    from pyball.domain.player.models import PlayerId


def build_active_match_response(container: Container) -> dict:
    """Build the response dict for GET /api/match/active, or raise 404."""
    try:
        meetup = container.get_active_meetup().execute(require_teams=True)
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No active match found") from exc
    assert meetup.teams is not None  # guaranteed by require_teams=True

    current = meetup.current_match()
    if current is None:
        raise HTTPException(404, "No active match found")

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text

    index_a = meetup.teams.index(current.teams_playing[0])
    index_b = meetup.teams.index(current.teams_playing[1])
    team_a = sorted_names(current.teams_playing[0].players, player_names)
    team_b = sorted_names(current.teams_playing[1].players, player_names)

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "teamA": team_a,
        "teamB": team_b,
        "nameA": colors[index_a].capitalize(),
        "nameB": colors[index_b].capitalize(),
        "colorA": hex_bg[index_a],
        "colorB": hex_bg[index_b],
        "colorTextA": hex_text[index_a],
        "colorTextB": hex_text[index_b],
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
        return {
            "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "location": meetup.location,
            "players": players,
            "teams": None,
            "locked": meetup.locked,
            "signupOpen": meetup.is_signup_open(),
        }

    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text
    emojis = container.team_emojis

    team_a = sorted_names(meetup.teams[0].players, player_names)
    team_b = sorted_names(meetup.teams[1].players, player_names)

    match_url = container.match_link_builder().build()

    teams_payload = {
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
        "goalkeeperA": (
            str(meetup.teams[0].goalkeeper.value) if meetup.teams[0].goalkeeper else None
        ),
        "goalkeeperB": (
            str(meetup.teams[1].goalkeeper.value) if meetup.teams[1].goalkeeper else None
        ),
        "matchUrl": match_url,
        "hasRecordedResults": any(match.result is not None for match in meetup.matches),
    }
    if len(meetup.teams) == 3:
        teams_payload.update(
            {
                "teamC": sorted_names(meetup.teams[2].players, player_names),
                "nameC": colors[2].capitalize(),
                "emojiC": emojis[2],
                "colorC": hex_bg[2],
                "colorTextC": hex_text[2],
                "goalkeeperC": (
                    str(meetup.teams[2].goalkeeper.value) if meetup.teams[2].goalkeeper else None
                ),
            }
        )

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "location": meetup.location,
        "players": players,
        "teams": teams_payload,
        "locked": meetup.locked,
        "signupOpen": meetup.is_signup_open(),
    }


def build_signup_meetup_response(container: Container, player_id: "PlayerId") -> dict:
    """Build the response for /api/signup/{meetup,join,leave}, or raise 404.

    Unlike build_meetup_active_response, this never exposes player IDs or
    management-only fields — only what a self-identified player needs to see.
    """
    try:
        meetup = container.get_active_meetup().execute()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No hay convocatoria activa") from exc

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    is_joined = player_id in meetup.players

    if meetup.teams is None:
        return {
            "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "location": meetup.location,
            "signupOpen": True,
            "roster": sorted_names(meetup.players, player_names),
            "isJoined": is_joined,
            "teams": None,
        }

    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text
    emojis = container.team_emojis
    teams_payload = [
        {
            "name": colors[index].capitalize(),
            "colorBg": hex_bg[index],
            "colorText": hex_text[index],
            "emoji": emojis[index],
            "players": _sorted_players_with_me(team.players, player_names, player_id),
        }
        for index, team in enumerate(meetup.teams)
    ]

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "location": meetup.location,
        "signupOpen": False,
        "roster": None,
        "isJoined": is_joined,
        "teams": teams_payload,
    }


def build_match_events_response(container: Container, meetup: Meetup) -> dict:
    """Serialise the most recent match's events and team data into a response dict."""
    assert meetup.teams is not None
    assert meetup.matches
    last_match = meetup.matches[-1]
    assert last_match.result is not None

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text

    index_a = meetup.teams.index(last_match.teams_playing[0])
    index_b = meetup.teams.index(last_match.teams_playing[1])
    team_a = sorted_names(last_match.teams_playing[0].players, player_names)
    team_b = sorted_names(last_match.teams_playing[1].players, player_names)

    events = [
        {
            "scorer": player_names.get(str(ev.scorer_id.value), "(desconocido)"),
            "assistant": (
                player_names.get(str(ev.assistant_id.value), "(desconocido)")
                if ev.assistant_id
                else None
            ),
            "team": ev.team,
            "timestamp": ev.timestamp.strftime("%H:%M"),
            "is_own_goal": ev.is_own_goal,
        }
        for ev in reversed(last_match.result.events)
    ]

    return {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "nameA": colors[index_a].capitalize(),
        "nameB": colors[index_b].capitalize(),
        "teamA": team_a,
        "teamB": team_b,
        "colorA": hex_bg[index_a],
        "colorB": hex_bg[index_b],
        "colorTextA": hex_text[index_a],
        "colorTextB": hex_text[index_b],
        "events": events,
    }


def sorted_names(player_ids, player_names: dict[str, str]) -> list[str]:
    """Return locale-sorted display names for a list of player IDs."""
    _sort = functools.cmp_to_key(locale.strcoll)
    return sorted(
        [player_names.get(str(pid.value), "(desconocido)") for pid in player_ids],
        key=_sort,
    )


def _sorted_players_with_me(
    player_ids, player_names: dict[str, str], me: "PlayerId"
) -> list[dict]:
    """Return locale-sorted {name, isMe} dicts for a team's players."""
    _sort = functools.cmp_to_key(locale.strcoll)
    return sorted(
        [
            {"name": player_names.get(str(pid.value), "(desconocido)"), "isMe": pid == me}
            for pid in player_ids
        ],
        key=lambda p: _sort(p["name"]),
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
