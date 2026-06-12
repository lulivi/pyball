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
"""Meetup route registrar and handlers."""
from __future__ import annotations

import functools
import locale
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException

from pyball.domain.meetup.errors import MeetupAlreadyClosedError, UnknownAlgorithmError
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.infrastructure.http.presenters import (
    build_meetup_active_response,
    serialise_callup_match,
)
from pyball.infrastructure.http.schemas import (
    AssignTeamsInput,
    CreateMeetupInput,
    GenerateTeamsInput,
    ParseCallupInput,
)

if TYPE_CHECKING:
    from pyball.application.container import Container


def register_meetup_routes(app: FastAPI, container: "Container") -> None:
    """Register meetup-related routes."""

    @app.get("/api/meetup/active")
    async def meetup_active():
        """Return the current active meetup with or without teams, or 404."""
        return build_meetup_active_response(container)

    @app.post("/api/meetup/parse-callup")
    async def parse_callup(body: ParseCallupInput):
        """Parse a WhatsApp callup text and fuzzy-match player names."""
        outcome = container.parse_callup().execute(body.text)
        return {
            "titulars": [serialise_callup_match(m) for m in outcome.titulars],
            "reserves": [serialise_callup_match(m) for m in outcome.reserves],
            "date": outcome.date.strftime("%Y-%m-%dT%H:%M"),
        }

    @app.post("/api/meetup/generate-teams")
    async def generate_teams_endpoint(body: GenerateTeamsInput):
        """Generate balanced teams for an existing meetup and return the full meetup state."""
        return _handle_generate_teams(container, body)

    @app.post("/api/meetup/assign-teams")
    async def assign_teams(body: AssignTeamsInput):
        """Manually assign players to specific teams by player ID."""
        try:
            meetup_date = datetime.fromisoformat(body.date)
        except ValueError as exc:
            raise HTTPException(
                422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM"
            ) from exc

        existing = container.meetup_repository.find_by_datetime(meetup_date)
        if existing is None:
            raise HTTPException(404, "No meetup found at the given date")
        if existing.is_closed():
            raise HTTPException(409, "Match already finished, cannot reassign teams")

        try:
            container.assign_teams_by_id().execute(meetup_date, body.team_a_ids, body.team_b_ids)
        except (ValueError, InvalidPlayerIdError) as exc:
            raise HTTPException(422, str(exc)) from exc

        return build_meetup_active_response(container)

    @app.post("/api/meetup/create")
    async def create_meetup_endpoint(body: CreateMeetupInput):
        """Create (or reset) a meetup with the given player list."""
        return _handle_create_meetup(container, body)


# ── Private helpers ───────────────────────────────────────────────────────────


def _handle_create_meetup(container: "Container", body: CreateMeetupInput) -> dict:
    """Validate, upsert via SetMeetupPlayers, and serialise the response."""
    try:
        meetup_date = datetime.fromisoformat(body.date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    try:
        meetup = container.set_meetup_players().execute(meetup_date, body.player_ids)
    except MeetupAlreadyClosedError as exc:
        raise HTTPException(409, "Match already finished, cannot reset") from exc
    except InvalidPlayerIdError as exc:
        raise HTTPException(422, str(exc)) from exc

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
    return {"date": meetup.date.strftime("%Y-%m-%dT%H:%M"), "players": players, "teams": None}


def _handle_generate_teams(container: "Container", body: GenerateTeamsInput) -> dict:
    """Validate, generate teams, and serialise the response for POST /api/meetup/generate-teams."""
    try:
        meetup_date = datetime.fromisoformat(body.date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    existing = container.meetup_repository.find_by_datetime(meetup_date)
    if existing is None:
        raise HTTPException(404, "No meetup found at the given date")
    if existing.is_closed():
        raise HTTPException(409, "Match already finished, cannot regenerate teams")

    try:
        container.create_teams(body.algorithm).execute(meetup_date)
    except (UnknownAlgorithmError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc

    return build_meetup_active_response(container)
