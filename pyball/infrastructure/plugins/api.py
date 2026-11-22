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
"""The versioned plugin API, mounted at /api/v1 with its own OpenAPI schema."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncIterable, AsyncIterator, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    InvalidCapacityError,
    InvalidMeetupIdError,
    MeetupAlreadyClosedError,
    MeetupFullError,
    MeetupHasRecordedResultsError,
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    SignupClosedError,
    UnknownAlgorithmError,
)
from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.plugins.schemas import (
    EventOut,
    MeetupOut,
    PlayerOut,
    meetup_out,
    player_out,
)

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier
    from pyball.infrastructure.plugins.auth import PluginCredentials
    from pyball.infrastructure.plugins.event_log import EventLog


class CreateMeetupBody(BaseModel):
    """Body of POST /meetups; location and capacity default to the club's."""

    date: datetime
    location: str | None = None
    capacity: int | None = Field(default=None, ge=2)


class LineupBody(BaseModel):
    """Body of PUT /meetups/{id}/lineup: the final roster and, optionally, how to make teams."""

    players: list[str]
    team_algorithm: str | None = None
    team_count: int = Field(default=2, ge=2, le=3)


class CapacityBody(BaseModel):
    """Body of PUT /meetups/{id}/capacity."""

    capacity: int = Field(ge=2)


def create_plugin_api(  # pylint: disable=too-many-locals,too-many-statements
    container: "Container", notifier: "MatchNotifier", credentials: "PluginCredentials"
) -> FastAPI:
    """Build the /api/v1 application: one call per logical plugin action, one event each."""
    api = FastAPI(
        title="PyBall plugin API",
        version="1",
        description=(
            "Stable contract for PyBall plugins. Authenticate with "
            "`Authorization: Bearer <PYBALL_API_TOKEN>`."
        ),
    )
    players_read = [Depends(credentials.require("players:read"))]
    meetups_read = [Depends(credentials.require("meetups:read"))]
    meetups_write = [Depends(credentials.require("meetups:write"))]

    @api.get("/players", response_model=list[PlayerOut], dependencies=players_read)
    async def list_players():
        """List every player."""
        return [player_out(p) for p in container.player_repository.find_all()]

    @api.get(
        "/meetups/active",
        response_model=MeetupOut,
        responses={404: {"description": "No active meetup"}},
        dependencies=meetups_read,
    )
    async def active_meetup():
        """Return the active meetup: the latest one not closed yet."""
        return meetup_out(_active(container))

    @api.post("/meetups", response_model=MeetupOut, status_code=201, dependencies=meetups_write)
    async def create_meetup(body: CreateMeetupBody):
        """Create an empty meetup; 409 if one exists at that date."""
        try:
            meetup = container.create_meetup().execute(
                body.date.replace(tzinfo=None), body.location, body.capacity
            )
        except DuplicateMeetupError as exc:
            raise HTTPException(409, "A meetup already exists at that date") from exc
        await notifier.on_meetup_created(meetup)
        return meetup_out(meetup)

    @api.delete("/meetups/{meetup_id}", response_model=MeetupOut, dependencies=meetups_write)
    async def cancel_meetup(meetup_id: str):
        """Cancel the active meetup; 409 for any other meetup or one with results."""
        if _meetup(container, meetup_id).id != _active(container).id:
            raise HTTPException(409, "Only the active meetup can be cancelled")
        meetup = _guarded(container.cancel_meetup().execute)
        await notifier.on_meetup_cancelled(meetup)
        return meetup_out(meetup)

    @api.put(
        "/meetups/{meetup_id}/players/{player_id}",
        response_model=MeetupOut,
        dependencies=meetups_write,
    )
    async def join(meetup_id: str, player_id: str):
        """Add a player to the roster; nothing happens if they are already in."""
        meetup = _meetup(container, meetup_id)
        player = _player(container, player_id)
        if player.id in meetup.players:
            return meetup_out(meetup)
        updated = _guarded(
            lambda: container.add_player_to_meetup_by_id().execute(meetup.date, player.id)
        )
        await notifier.on_player_joined(updated, player, player.group == "substitute")
        return meetup_out(updated)

    @api.delete(
        "/meetups/{meetup_id}/players/{player_id}",
        response_model=MeetupOut,
        dependencies=meetups_write,
    )
    async def leave(meetup_id: str, player_id: str):
        """Remove a player from the roster."""
        meetup = _meetup(container, meetup_id)
        player = _player(container, player_id)
        updated = _guarded(
            lambda: container.remove_player_from_meetup_by_id().execute(meetup.date, player.id)
        )
        await notifier.on_player_left(updated, player, player.group == "substitute")
        return meetup_out(updated)

    @api.put("/meetups/{meetup_id}/lineup", response_model=MeetupOut, dependencies=meetups_write)
    async def set_lineup(meetup_id: str, body: LineupBody):
        """Replace the roster and, with team_algorithm, build the teams: one step, one event."""
        meetup = _meetup(container, meetup_id)
        ids = [_player(container, pid).id for pid in body.players]
        updated = _guarded(
            lambda: container.set_lineup(body.team_algorithm).execute(
                meetup.date, ids, body.team_count
            )
        )
        await notifier.on_meetup_updated(updated)
        return meetup_out(updated)

    @api.put("/meetups/{meetup_id}/capacity", response_model=MeetupOut, dependencies=meetups_write)
    async def set_capacity(meetup_id: str, body: CapacityBody):
        """Set how many players the meetup plays with."""
        meetup = _meetup(container, meetup_id)
        updated = _guarded(
            lambda: container.set_meetup_capacity().execute(meetup.date, body.capacity)
        )
        await notifier.on_meetup_updated(updated)
        return meetup_out(updated)

    @api.post(
        "/meetups/{meetup_id}/substitute-search",
        response_model=MeetupOut,
        dependencies=meetups_write,
    )
    async def open_search(meetup_id: str):
        """Open the substitute search; 409 if the roster is full or teams exist.

        Opening a search that is already open changes nothing and announces nothing.
        """
        meetup = _meetup(container, meetup_id)
        if meetup.substitute_search:
            return meetup_out(meetup)
        updated = _guarded(lambda: container.open_substitute_search().execute(meetup.date))
        await notifier.on_substitute_search_opened(updated)
        return meetup_out(updated)

    @api.delete(
        "/meetups/{meetup_id}/substitute-search",
        response_model=MeetupOut,
        dependencies=meetups_write,
    )
    async def close_search(meetup_id: str):
        """Close the substitute search."""
        meetup = _meetup(container, meetup_id)
        updated = _guarded(lambda: container.close_substitute_search().execute(meetup.date))
        await notifier.on_meetup_updated(updated)
        return meetup_out(updated)

    @api.get("/events", dependencies=meetups_read, response_class=EventSourceResponse)
    async def events(
        after: int | None = Query(default=None, ge=0),
        last_event_id: int | None = Header(default=None, ge=0),
    ) -> AsyncIterable[EventOut]:
        """Stream events as server-sent events, each with its id, type and JSON data.

        Resume with the Last-Event-ID header or ?after=<id> to receive every later event in
        order, then the live ones; ?after=0 replays the whole log. With neither, only new
        events are sent. An idle stream sends a `: ping` comment every 15 s.
        """
        seen = last_event_id if last_event_id is not None else after
        async for event in event_stream(container.event_log, seen):
            # The annotation documents each item's data as EventOut in the OpenAPI schema;
            # FastAPI sends ServerSentEvent items as they are, with their id and type.
            yield ServerSentEvent(  # type: ignore[misc]
                data=event, event=event["type"], id=str(event["id"])
            )

    return api


async def event_stream(log: "EventLog", after: int | None) -> AsyncIterator[dict[str, Any]]:
    """Yield the events after ``after`` (none if None), then live ones.

    Ends when the log closes its subscribers, on shutdown.
    """
    last_id, queue = log.subscribe()
    try:
        for event in log.after(last_id if after is None else after, up_to=last_id):
            yield event
        while (live := await queue.get()) is not None:
            yield live
    finally:
        log.unsubscribe(queue)


def _active(container: "Container") -> Meetup:
    try:
        return container.get_active_meetup().execute()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No active meetup") from exc


def _meetup(container: "Container", meetup_id: str) -> Meetup:
    try:
        meetup = container.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
    except InvalidMeetupIdError as exc:
        raise HTTPException(404, "No such meetup") from exc
    if meetup is None:
        raise HTTPException(404, "No such meetup")
    return meetup


def _player(container: "Container", player_id: str) -> Player:
    try:
        player = container.player_repository.find_by_id(PlayerId.from_string(player_id))
    except InvalidPlayerIdError as exc:
        raise HTTPException(422, f"Unknown player {player_id}") from exc
    if player is None:
        raise HTTPException(422, f"Unknown player {player_id}")
    return player


def _guarded(change: Callable[[], Meetup]) -> Meetup:
    """Run a use case, mapping its domain refusals to HTTP errors."""
    try:
        return change()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No such meetup") from exc
    except (
        SignupClosedError,
        MeetupFullError,
        MeetupAlreadyClosedError,
        MeetupHasRecordedResultsError,
        PlayerNotInMeetupError,
    ) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (InvalidCapacityError, UnknownAlgorithmError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
