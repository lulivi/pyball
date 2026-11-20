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
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable, cast

from fastapi import FastAPI, HTTPException

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    InvalidCapacityError,
    MeetupAlreadyClosedError,
    MeetupFullError,
    MeetupHasNoTeamsError,
    MeetupHasRecordedResultsError,
    MeetupNotFoundError,
    SignupClosedError,
    UnknownAlgorithmError,
)
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.infrastructure.http.presenters import (
    build_meetup_active_response,
    serialise_callup_match,
)
from pyball.infrastructure.http.schemas import (
    AssignTeamsInput,
    CreateMeetupInput,
    GenerateTeamsInput,
    MeetupCapacityInput,
    MeetupDateInput,
    ParseCallupInput,
    UpdateMeetupDateInput,
    UpdateMeetupLocationInput,
)

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier
    from pyball.domain.meetup.models import Meetup


def register_meetup_routes(
    app: FastAPI,
    container: "Container",
    notifier: "MatchNotifier",
    enable_web_signup: bool = False,
) -> None:
    """Register meetup-related routes."""

    @app.get("/api/meetup/active")
    async def meetup_active():
        """Return the current active meetup with or without teams, or 404."""
        return build_meetup_active_response(container, enable_web_signup)

    @app.get("/api/meetup/history")
    async def meetup_history():
        """Return closed meetups (date, location), newest first."""
        closed = [m for m in container.meetup_repository.find_all() if m.is_closed()]
        closed.sort(key=lambda m: m.date, reverse=True)
        return [
            {"date": m.date.strftime("%Y-%m-%dT%H:%M"), "location": m.location} for m in closed
        ]

    @app.delete("/api/meetup/active")
    async def cancel_meetup_endpoint():
        """Delete the active meetup, or 404/409 if none exists or it has a recorded result."""
        try:
            meetup = container.cancel_meetup().execute()
        except MeetupNotFoundError as exc:
            raise HTTPException(404, "No active meetup to cancel") from exc
        except MeetupHasRecordedResultsError as exc:
            raise HTTPException(409, "Meetup has a recorded result, cannot cancel") from exc
        await notifier.on_meetup_cancelled(meetup)
        return {"status": "cancelled", "date": meetup.date.strftime("%Y-%m-%dT%H:%M")}

    @app.post("/api/meetup/close")
    async def close_meetup_endpoint():
        """Close the active meetup, or 404/409 if none exists or it's already closed.

        Mainly for ending a triangular session — a classic meetup closes itself
        automatically once its one match gets a result.
        """
        try:
            meetup = container.get_active_meetup().execute()
        except MeetupNotFoundError as exc:
            raise HTTPException(404, "No active meetup to close") from exc
        try:
            closed = container.close_meetup().execute(meetup.date)
        except MeetupAlreadyClosedError as exc:
            raise HTTPException(409, "Meetup already closed") from exc
        await notifier.on_match_closed(closed)
        return {"status": "closed", "date": closed.date.strftime("%Y-%m-%dT%H:%M")}

    @app.post("/api/meetup/parse-callup")
    async def parse_callup(body: ParseCallupInput):
        """Parse a callup text and fuzzy-match player names."""
        outcome = container.parse_callup().execute(body.text)
        return {
            "titulars": [serialise_callup_match(m) for m in outcome.titulars],
            "reserves": [serialise_callup_match(m) for m in outcome.reserves],
            "date": outcome.date.strftime("%Y-%m-%dT%H:%M"),
        }

    @app.post("/api/meetup/generate-teams")
    async def generate_teams_endpoint(body: GenerateTeamsInput):
        """Generate balanced teams for an existing meetup and return the full meetup state."""
        return await _handle_generate_teams(container, notifier, body, enable_web_signup)

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
            meetup = container.assign_teams_by_id().execute(
                meetup_date,
                body.team_a_ids,
                body.team_b_ids,
                body.team_c_ids,
                body.team_a_goalkeeper_id,
                body.team_b_goalkeeper_id,
                body.team_c_goalkeeper_id,
            )
        except (ValueError, InvalidPlayerIdError) as exc:
            raise HTTPException(422, str(exc)) from exc

        await notifier.on_meetup_updated(meetup)
        return build_meetup_active_response(container, enable_web_signup)

    @app.post("/api/meetup/destroy-teams")
    async def destroy_teams_endpoint(body: MeetupDateInput):
        """Destroy the meetup's teams and reopen signup, or 404/409."""
        return await _handle_destroy_teams(container, notifier, body, enable_web_signup)

    @app.post("/api/meetup/create")
    async def create_meetup_endpoint(body: CreateMeetupInput):
        """Create (or reset) a meetup with the given player list."""
        return await _handle_create_meetup(container, notifier, body, enable_web_signup)

    @app.post("/api/meetup/create-next")
    async def create_next_meetup_endpoint():
        """Create an empty meetup at the next occurrence of the default weekday/hour."""
        return await _handle_create_next_meetup(container, notifier, enable_web_signup)

    @app.post("/api/meetup/date")
    async def update_meetup_date_endpoint(body: UpdateMeetupDateInput):
        """Move a meetup to a new date."""
        return await _handle_update_meetup_date(container, notifier, body)

    @app.post("/api/meetup/location")
    async def update_meetup_location_endpoint(body: UpdateMeetupLocationInput):
        """Change a meetup's location."""
        return await _handle_update_meetup_location(container, notifier, body)

    @app.post("/api/meetup/capacity")
    async def set_meetup_capacity_endpoint(body: MeetupCapacityInput):
        """Set how many players the meetup plays with, or 404/409/422."""
        meetup_date = _parse_date(body.date)
        meetup = _run_meetup_change(
            lambda: container.set_meetup_capacity().execute(meetup_date, body.capacity)
        )
        await notifier.on_meetup_updated(meetup)
        return build_meetup_active_response(container, enable_web_signup)

    @app.post("/api/meetup/substitute-search/open")
    async def open_substitute_search_endpoint(body: MeetupDateInput):
        """Open the meetup's substitute search, or 404/409; reopening announces nothing."""
        meetup_date = _parse_date(body.date)
        current = container.meetup_repository.find_by_datetime(meetup_date)
        if current is not None and current.substitute_search:
            return build_meetup_active_response(container, enable_web_signup)
        meetup = _run_meetup_change(
            lambda: container.open_substitute_search().execute(meetup_date)
        )
        await notifier.on_substitute_search_opened(meetup)
        return build_meetup_active_response(container, enable_web_signup)

    @app.post("/api/meetup/substitute-search/close")
    async def close_substitute_search_endpoint(body: MeetupDateInput):
        """Close the meetup's substitute search, or 404."""
        meetup_date = _parse_date(body.date)
        meetup = _run_meetup_change(
            lambda: container.close_substitute_search().execute(meetup_date)
        )
        await notifier.on_meetup_updated(meetup)
        return build_meetup_active_response(container, enable_web_signup)


# ── Private helpers ───────────────────────────────────────────────────────────


async def _handle_create_meetup(
    container: "Container",
    notifier: "MatchNotifier",
    body: CreateMeetupInput,
    enable_web_signup: bool,
) -> dict:
    """Validate, upsert via SetMeetupPlayers, notify, and serialise the response."""
    try:
        meetup_date = datetime.fromisoformat(body.date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    existed_before = container.meetup_repository.find_by_datetime(meetup_date) is not None

    try:
        meetup = container.set_meetup_players().execute(meetup_date, body.player_ids)
    except MeetupAlreadyClosedError as exc:
        raise HTTPException(409, "Match already finished, cannot reset") from exc
    except MeetupHasRecordedResultsError as exc:
        raise HTTPException(409, "Meetup has a recorded result, cannot reset the roster") from exc
    except InvalidPlayerIdError as exc:
        raise HTTPException(422, str(exc)) from exc

    if existed_before:
        await notifier.on_meetup_updated(meetup)
    else:
        await notifier.on_meetup_created(meetup)

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_positions = {str(p.id.value): p.position for p in all_players}
    _sort = functools.cmp_to_key(locale.strcoll)
    players = sorted(
        [
            {
                "id": str(pid.value),
                "name": player_names.get(str(pid.value), "(desconocido)"),
                "position": player_positions.get(str(pid.value)),
            }
            for pid in meetup.players
        ],
        key=lambda p: _sort(cast(str, p["name"])),
    )
    response = {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "players": players,
        "teams": None,
        "location": meetup.location,
        "capacity": meetup.capacity,
        "substituteSearch": meetup.substitute_search,
    }
    if enable_web_signup:
        response["signupUrl"] = container.signup_link_builder().build()
    return response


async def _handle_create_next_meetup(
    container: "Container", notifier: "MatchNotifier", enable_web_signup: bool
) -> dict:
    """Create an empty meetup at the next default weekday/hour and notify."""
    next_date = _get_next_default_date(container.default_week_day, container.default_hour)
    try:
        meetup = container.create_meetup().execute(next_date)
    except DuplicateMeetupError as exc:
        raise HTTPException(409, "A meetup already exists at the next default date") from exc

    await notifier.on_meetup_created(meetup)
    response: dict = {
        "date": meetup.date.strftime("%Y-%m-%dT%H:%M"),
        "players": [],
        "teams": None,
        "location": meetup.location,
        "capacity": meetup.capacity,
        "substituteSearch": meetup.substitute_search,
    }
    if enable_web_signup:
        response["signupUrl"] = container.signup_link_builder().build()
    return response


async def _handle_generate_teams(
    container: "Container",
    notifier: "MatchNotifier",
    body: GenerateTeamsInput,
    enable_web_signup: bool,
) -> dict:
    """Validate, generate teams, notify, and serialise the active meetup response."""
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
        meetup = container.create_teams(body.algorithm).execute(meetup_date, body.team_count)
    except (UnknownAlgorithmError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except MeetupHasRecordedResultsError as exc:
        raise HTTPException(409, "Meetup has a recorded result, cannot regenerate teams") from exc

    await notifier.on_meetup_updated(meetup)
    return build_meetup_active_response(container, enable_web_signup)


async def _handle_destroy_teams(
    container: "Container",
    notifier: "MatchNotifier",
    body: MeetupDateInput,
    enable_web_signup: bool,
) -> dict:
    """Validate, destroy the meetup's teams, notify, and return the active meetup response."""
    try:
        meetup_date = datetime.fromisoformat(body.date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    try:
        meetup = container.destroy_teams().execute(meetup_date)
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No meetup found at the given date") from exc
    except MeetupHasNoTeamsError as exc:
        raise HTTPException(409, "Cannot destroy teams: meetup has no teams") from exc
    except MeetupHasRecordedResultsError as exc:
        raise HTTPException(
            409, "Cannot destroy teams: a match result is already recorded"
        ) from exc

    await notifier.on_meetup_updated(meetup)
    return build_meetup_active_response(container, enable_web_signup)


async def _handle_update_meetup_date(
    container: "Container", notifier: "MatchNotifier", body: UpdateMeetupDateInput
) -> dict:
    """Validate, move the meetup's date, notify, and return the new date/location."""
    try:
        old_date = datetime.fromisoformat(body.old_date)
        new_date = datetime.fromisoformat(body.new_date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    try:
        meetup = container.update_meetup_date().execute(old_date, new_date)
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No meetup found at old_date") from exc
    except DuplicateMeetupError as exc:
        raise HTTPException(409, "A meetup already exists at new_date") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    await notifier.on_meetup_date_changed(old_date, meetup)
    return {"date": meetup.date.strftime("%Y-%m-%dT%H:%M"), "location": meetup.location}


async def _handle_update_meetup_location(
    container: "Container", notifier: "MatchNotifier", body: UpdateMeetupLocationInput
) -> dict:
    """Validate, update the meetup's location, notify, and return the new date/location."""
    try:
        meetup_date = datetime.fromisoformat(body.date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc

    try:
        meetup = container.update_meetup_location().execute(meetup_date, body.location)
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No meetup found at date") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    await notifier.on_meetup_updated(meetup)
    return {"date": meetup.date.strftime("%Y-%m-%dT%H:%M"), "location": meetup.location}


def _parse_date(value: str) -> datetime:
    """Parse an ISO meetup date from a request body, or 422."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM") from exc


def _run_meetup_change(change: Callable[[], Meetup]) -> Meetup:
    """Run a capacity or substitute search change, mapping domain errors to HTTP errors."""
    try:
        return change()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No meetup found at the given date") from exc
    except SignupClosedError as exc:
        raise HTTPException(409, "Los equipos ya están hechos") from exc
    except MeetupFullError as exc:
        raise HTTPException(409, "Ya estáis completos") from exc
    except InvalidCapacityError as exc:
        raise HTTPException(422, "La capacidad debe ser al menos 2") from exc


def _get_next_default_date(
    default_week_day: str, default_hour: str, now: datetime | None = None
) -> datetime:
    """Compute the next occurrence of the configured default weekday/hour."""
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    target_weekday = day_map.get(default_week_day.lower(), 2)
    reference = now or datetime.now()
    days_until_target = (target_weekday - reference.weekday() + 7) % 7
    if days_until_target == 0:
        days_until_target = 7
    next_date = reference + timedelta(days=days_until_target)
    hour, minute = map(int, default_hour.split(":"))
    return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
