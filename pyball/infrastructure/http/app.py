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
"""FastAPI application factory."""
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pyball.application.meetup import FormatMatchSummary, ParseCallupText
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.domain.player.models import PlayerId

try:
    from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer as _StatsRenderer

    _STATS_AVAILABLE = True
except ImportError:
    _STATS_AVAILABLE = False

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier

logger = logging.getLogger(__name__)


# ── Pydantic request/response models ──────────────────────────────────────────


class GoalEventInput(BaseModel):
    """Pydantic model for a single goal event from the frontend."""

    scorer: str
    assistant: str | None
    team: str
    timestamp: str


class FinalScore(BaseModel):
    """Pydantic model for the final score."""

    A: int
    B: int


class FinishMatchInput(BaseModel):
    """Pydantic model for the POST /api/match/finish request body."""

    meetup_date: str
    events: list[GoalEventInput]
    finalScore: FinalScore


class ParseCallupInput(BaseModel):
    """Request body for POST /api/meetup/parse-callup."""

    text: str


class CreateWithTeamsInput(BaseModel):
    """Request body for POST /api/meetup/create-with-teams."""

    date: str
    player_ids: list[str]
    algorithm: str = "balanceado"


# ── App factory ───────────────────────────────────────────────────────────────


def create_app(
    container: "Container",
    notifier: "MatchNotifier",
    static_dir: Path = Path("static"),
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="PyBall API")

    _register_health(app, static_dir)
    _register_match_routes(app, container, notifier)
    _register_player_routes(app, container)
    _register_meetup_routes(app, container)

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


class _Server(uvicorn.Server):
    """Uvicorn server that defers signal handling to the caller."""

    def install_signal_handlers(self) -> None:
        """No-op: signals are managed by the entrypoint."""


# ── Route registrars ──────────────────────────────────────────────────────────


def _register_health(app: FastAPI, static_dir: Path) -> None:
    """Register the health-check and static-page routes."""

    @app.get("/")
    async def health():
        """Return a simple status response."""
        return {"status": "ok"}

    @app.get("/match")
    async def match_page():
        """Serve the match tracker SPA."""
        return FileResponse(static_dir / "match.html")


def _register_match_routes(
    app: FastAPI, container: "Container", notifier: "MatchNotifier"
) -> None:
    """Register match-related routes."""

    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and notify via the configured notifier."""
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
            logger.info("finish_match: meetup result set: %s", meetup.result)
        except MeetupNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meetup not found") from exc
        except MeetupAlreadyClosedError as exc:
            raise HTTPException(status_code=409, detail="Match already closed") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        await notifier.on_match_closed(meetup)

        return {
            "meetup_date": body.meetup_date,
            "score_a": meetup.result.score_a,
            "score_b": meetup.result.score_b,
        }

    @app.get("/api/match/latest")
    async def latest_match():
        """Return the date of the most recent finished meetup."""
        all_meetups = container.meetup_repository.find_all()
        finished = [m for m in all_meetups if m.result is not None]
        if not finished:
            raise HTTPException(404, "No finished matches found")
        latest = max(finished, key=lambda m: m.date)
        return {"date": latest.date.strftime("%Y-%m-%dT%H:%M")}

    @app.get("/api/match/{date}/summary")
    async def match_summary(date: str):
        """Return the WhatsApp-format summary for a finished match."""
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
        name_a, name_b = container.team_display_names

        message = FormatMatchSummary().execute(
            meetup, player_names, team_display_names=(name_a, name_b)
        )
        date_label = meetup.date.strftime("%-d %B").title()
        return {"date_label": date_label, "message": message}

    @app.get("/api/match/{date}/stats.png")
    async def match_stats_image(date: str):
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


def _register_player_routes(app: FastAPI, container: "Container") -> None:
    """Register player-related routes."""

    @app.get("/api/players")
    async def list_players():
        """Return all registered players."""
        players = container.player_repository.find_all()
        return [{"id": str(p.id.value), "name": p.name} for p in players]


def _register_meetup_routes(app: FastAPI, container: "Container") -> None:
    """Register meetup-related routes."""

    @app.post("/api/meetup/parse-callup")
    async def parse_callup(body: ParseCallupInput):
        """Parse a WhatsApp callup text and fuzzy-match player names."""
        players = container.player_repository.find_all()
        result = ParseCallupText().execute(body.text, players)

        return {
            "titulars": [_serialise_match(m) for m in result.titulars],
            "reserves": [_serialise_match(m) for m in result.reserves],
        }

    @app.post("/api/meetup/create-with-teams")
    async def create_with_teams(body: CreateWithTeamsInput):
        """Create (or reset) a meetup, generate balanced teams, return match URL."""
        try:
            meetup_date = datetime.fromisoformat(body.date)
        except ValueError as exc:
            raise HTTPException(
                422, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM"
            ) from exc

        existing = container.meetup_repository.find_by_datetime(meetup_date)
        if existing and existing.is_closed():
            raise HTTPException(409, "Match already finished, cannot regenerate teams")

        if existing:
            existing.players.clear()
            existing.clear_teams()
            for pid_str in body.player_ids:
                existing.add_player(PlayerId.from_string(pid_str))
            container.meetup_repository.save(existing)
        else:
            meetup = container.create_meetup().execute(meetup_date)
            for pid_str in body.player_ids:
                meetup.add_player(PlayerId.from_string(pid_str))
            container.meetup_repository.save(meetup)

        try:
            container.create_teams(body.algorithm).execute(meetup_date)
        except Exception as exc:
            raise HTTPException(422, str(exc)) from exc

        match_url = container.start_match().execute(meetup_date)

        saved_meetup = container.meetup_repository.find_by_datetime(meetup_date)
        if saved_meetup is None or saved_meetup.teams is None:
            raise HTTPException(500, "Failed to retrieve meetup after team creation")

        all_players = container.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}
        name_a, name_b = container.team_display_names
        team_a = [player_names[str(pid.value)] for pid in saved_meetup.teams[0].players]
        team_b = [player_names[str(pid.value)] for pid in saved_meetup.teams[1].players]

        return {
            "team_a": team_a,
            "team_b": team_b,
            "name_a": name_a,
            "name_b": name_b,
            "match_url": match_url,
        }


# ── Private helpers ───────────────────────────────────────────────────────────


def _serialise_match(match) -> dict:
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
