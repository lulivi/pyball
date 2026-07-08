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
"""Match route registrar and handlers."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.infrastructure.http.presenters import (
    build_active_match_response,
    build_match_events_response,
    sorted_names,
)
from pyball.infrastructure.http.schemas import FinishMatchInput

try:
    from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer as _StatsRenderer

    _STATS_AVAILABLE = True
except ImportError:
    _STATS_AVAILABLE = False

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier

logger = logging.getLogger(__name__)


def register_match_routes(app: FastAPI, container: "Container", notifier: "MatchNotifier") -> None:
    """Register match-related routes."""

    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and notify via the configured notifier."""
        return await _handle_finish_match(container, notifier, body)

    @app.get("/api/match/latest")
    async def latest_match():
        """Return the date of the most recent finished meetup."""
        all_meetups = container.meetup_repository.find_all()
        finished = [m for m in all_meetups if m.matches and m.matches[-1].result is not None]
        if not finished:
            raise HTTPException(404, "No finished matches found")
        latest = max(finished, key=lambda m: m.date)
        return {"date": latest.date.strftime("%Y-%m-%dT%H:%M")}

    @app.get("/api/match/active")
    async def active_match():
        """Return the current unfinished meetup with teams, or 404."""
        return build_active_match_response(container)

    @app.get("/api/match/{date}/summary")
    async def match_summary(date: str):
        """Return the WhatsApp-format summary for a finished match."""
        return _handle_match_summary(container, date)

    @app.get("/api/match/{date}/stats.png")
    async def match_stats_image(date: str):
        """Generate and return the stats PNG for the given date."""
        return await _handle_match_stats_image(container, date)

    @app.get("/api/match/{date}/events")
    async def match_events(date: str):
        """Return events of a closed match with player IDs resolved to names."""
        return _handle_match_events(container, date)

    @app.post("/api/match/{date}/edit")
    async def edit_match(date: str, body: FinishMatchInput):
        """Replace the result of a closed match and re-fire the Telegram notification."""
        logger.info("edit_match called: date=%s", date)
        return await _handle_edit_match(container, notifier, date, body)


# ── Private helpers ───────────────────────────────────────────────────────────


async def _handle_finish_match(
    container: "Container",
    notifier: "MatchNotifier",
    body: FinishMatchInput,
) -> dict:
    """Execute the finish-match use case, notify if closed, and return the result."""
    logger.info(
        "finish_match called: meetup_date=%s, finalScore=%s",
        body.meetup_date,
        body.finalScore,
    )
    use_case = container.finish_match()
    events = [e.model_dump() for e in body.events]
    try:
        meetup = use_case.execute(
            body.meetup_date, events, {"A": body.finalScore.A, "B": body.finalScore.B}
        )
    except MeetupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Meetup not found") from exc
    except MeetupAlreadyClosedError as exc:
        raise HTTPException(status_code=409, detail="Match already closed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    just_finished = meetup.matches[-2] if not meetup.is_closed() else meetup.matches[-1]
    logger.info("finish_match: match result set: %s", just_finished.result)

    response = {
        "meetup_date": body.meetup_date,
        "score_a": just_finished.result.score_a,
        "score_b": just_finished.result.score_b,
    }

    if meetup.is_closed():
        await notifier.on_match_closed(meetup)
    else:
        current = meetup.current_match()
        player_names = {str(p.id.value): p.name for p in container.player_repository.find_all()}
        colors = container.team_colors
        hex_bg = container.team_hex_bg
        hex_text = container.team_hex_text
        response["next_round"] = {
            "teamA": sorted_names(current.teams_playing[0].players, player_names),
            "teamB": sorted_names(current.teams_playing[1].players, player_names),
            "nameA": colors[0].capitalize(),
            "nameB": colors[1].capitalize(),
            "colorA": hex_bg[0],
            "colorB": hex_bg[1],
            "colorTextA": hex_text[0],
            "colorTextB": hex_text[1],
        }

    return response


def _handle_match_summary(container: "Container", date: str) -> dict:
    """Fetch, validate, and serialise the WhatsApp-format summary for a finished match."""
    try:
        meetup_date = datetime.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format") from exc

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if meetup is None:
        raise HTTPException(404, "Meetup not found")
    if not meetup.is_closed():
        raise HTTPException(409, "Match not finished yet")

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}

    message = container.format_match_summary().execute(
        meetup,
        player_names,
        team_colors=container.team_colors,
        team_emojis=container.team_emojis,
        legacy_stats=container.legacy_stats,
    )
    date_label = meetup.date.strftime("%-d %B").title()
    return {"date_label": date_label, "message": message}


async def _handle_match_stats_image(container: "Container", date: str) -> Response:
    """Generate and return the stats PNG for the given date."""
    if not _STATS_AVAILABLE:
        raise HTTPException(503, "Stats image generation not available")

    try:
        meetup_date = datetime.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format") from exc

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if meetup is None:
        raise HTTPException(404, "Meetup not found")
    if not meetup.is_closed():
        raise HTTPException(409, "Match not finished yet")

    report = container.compute_stats().execute()
    renderer = _StatsRenderer()
    png_bytes = await renderer.render(report, scope="season")

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="stats-{date}.png"'},
    )


def _handle_match_events(container: "Container", date: str) -> dict:
    """Validate, look up, and serialise events for a closed match."""
    try:
        meetup_date = datetime.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format") from exc

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if meetup is None:
        raise HTTPException(404, "Meetup not found")
    if not meetup.is_closed():
        raise HTTPException(409, "Match is not closed yet")
    if not meetup.matches or meetup.matches[-1].result is None:
        raise HTTPException(409, "Match has no result")

    return build_match_events_response(container, meetup)


async def _handle_edit_match(
    container: "Container",
    notifier: "MatchNotifier",
    date: str,
    body: FinishMatchInput,
) -> dict:
    """Replace result of a closed match and announce the correction."""
    try:
        meetup_date = datetime.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format") from exc

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if meetup is None:
        raise HTTPException(404, "Meetup not found")
    if not meetup.is_closed():
        raise HTTPException(409, "Match is not closed; use POST /api/match/finish instead")

    events = [e.model_dump() for e in body.events]
    try:
        updated = container.edit_match_result().execute(
            date, events, {"A": body.finalScore.A, "B": body.finalScore.B}
        )
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "Meetup not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    await notifier.on_match_edited(updated)

    return {
        "meetup_date": date,
        "score_a": updated.matches[-1].result.score_a,
        "score_b": updated.matches[-1].result.score_b,
    }
