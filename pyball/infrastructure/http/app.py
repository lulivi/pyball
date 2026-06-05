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
import functools
import locale
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pyball.application.meetup import FormatMatchSummary, ParseCallupText
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.http.auth import TokenAuthMiddleware

try:
    from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer as _StatsRenderer

    _STATS_AVAILABLE = True
except ImportError:
    _STATS_AVAILABLE = False

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier
    from pyball.domain.meetup.models import Meetup

logger = logging.getLogger(__name__)


# ── Pydantic request/response models ──────────────────────────────────────────


class GoalEventInput(BaseModel):
    """Pydantic model for a single goal event from the frontend."""

    scorer: str
    assistant: str | None
    team: str
    timestamp: str
    is_own_goal: bool = False


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


class AssignTeamsInput(BaseModel):
    """Request body for POST /api/meetup/assign-teams."""

    date: str
    team_a_ids: list[str]
    team_b_ids: list[str]


# ── App factory ───────────────────────────────────────────────────────────────


def create_app(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    container: "Container",
    notifier: "MatchNotifier",
    static_dir: Path = Path("static"),
    match_token: str = "",
    manage_token: str = "",
    path_prefix: str = "",
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="PyBall API")

    if match_token or manage_token:
        app.add_middleware(TokenAuthMiddleware, match_token=match_token, manage_token=manage_token)

    _register_static(app, static_dir, container.name, path_prefix)
    _register_match_routes(app, container, notifier, path_prefix)
    _register_player_routes(app, container, path_prefix)
    _register_meetup_routes(app, container, path_prefix)

    if static_dir.exists():
        mount_path = f"/{path_prefix}" if path_prefix else "/"
        app.mount(mount_path, StaticFiles(directory=static_dir, html=True), name="static")

    return app


class _Server(uvicorn.Server):
    """Uvicorn server that defers signal handling to the caller."""

    def install_signal_handlers(self) -> None:
        """No-op: signals are managed by the entrypoint."""


# ── Route registrars ──────────────────────────────────────────────────────────


def _register_static(app: FastAPI, static_dir: Path, name: str, prefix: str) -> None:
    """Register the health-check, static-page, manifest, and SW routes."""
    base = f"/{prefix}" if prefix else ""

    @app.get(f"{base}/")
    async def health():
        """Return a simple status response."""
        return {"status": "ok"}

    @app.get(f"{base}/match")
    async def match_page():
        """Serve the match tracker SPA with prefix injected."""
        content = (static_dir / "match.html").read_text()
        return HTMLResponse(content.replace("__PYBALL_BASE__", base))

    @app.get(f"{base}/manage")
    async def manage_page():
        """Serve the manage tracker SPA with prefix injected."""
        content = (static_dir / "manage.html").read_text()
        return HTMLResponse(content.replace("__PYBALL_BASE__", base))

    @app.get(f"{base}/sw.js")
    async def service_worker():
        """Serve the service worker with prefix and slug injected."""
        content = (static_dir / "sw.js").read_text()
        slug = prefix if prefix else "default"
        content = content.replace("__PYBALL_BASE__", base).replace("__PYBALL_SLUG__", slug)
        return Response(content, media_type="application/javascript")

    _icons = [
        {"src": f"{base}/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": f"{base}/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ]

    @app.get(f"{base}/manifest-match.json")
    async def manifest_match():
        """Return the dynamic PWA manifest for the match page."""
        return {
            "name": f"PyBall – Partido {name}",
            "short_name": f"Partido {name}",
            "id": f"{base}/match",
            "scope": f"{base}/match",
            "start_url": f"{base}/match",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "icons": _icons,
        }

    @app.get(f"{base}/manifest-manage.json")
    async def manifest_manage():
        """Return the dynamic PWA manifest for the manage page."""
        return {
            "name": f"PyBall – Gestión {name}",
            "short_name": f"Gestión {name}",
            "id": f"{base}/manage",
            "scope": f"{base}/manage",
            "start_url": f"{base}/manage",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "icons": _icons,
        }


def _register_match_routes(
    app: FastAPI, container: "Container", notifier: "MatchNotifier", prefix: str
) -> None:
    """Register match-related routes."""
    base = f"/{prefix}" if prefix else ""

    @app.post(f"{base}/api/match/finish")
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

    @app.get(f"{base}/api/match/latest")
    async def latest_match():
        """Return the date of the most recent finished meetup."""
        all_meetups = container.meetup_repository.find_all()
        finished = [m for m in all_meetups if m.result is not None]
        if not finished:
            raise HTTPException(404, "No finished matches found")
        latest = max(finished, key=lambda m: m.date)
        return {"date": latest.date.strftime("%Y-%m-%dT%H:%M")}

    @app.get(f"{base}/api/match/active")
    async def active_match():
        """Return the current unfinished meetup with teams, or 404."""
        return _build_active_match_response(container)

    @app.get(f"{base}/api/match/{{date}}/summary")
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

        message = FormatMatchSummary().execute(
            meetup,
            player_names,
            team_colors=container.team_colors,
            team_emojis=container.team_emojis,
            legacy_stats=container.legacy_stats,
        )
        date_label = meetup.date.strftime("%-d %B").title()
        return {"date_label": date_label, "message": message}

    @app.get(f"{base}/api/match/{{date}}/stats.png")
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

    @app.get(f"{base}/api/match/{{date}}/events")
    async def match_events(date: str):
        """Return events of a closed match with player IDs resolved to names."""
        return _handle_match_events(container, date)

    @app.post(f"{base}/api/match/{{date}}/edit")
    async def edit_match(date: str, body: FinishMatchInput):
        """Replace the result of a closed match and re-fire the Telegram notification."""
        logger.info("edit_match called: date=%s", date)
        return await _handle_edit_match(container, notifier, date, body)


def _register_player_routes(app: FastAPI, container: "Container", prefix: str) -> None:
    """Register player-related routes."""
    base = f"/{prefix}" if prefix else ""

    @app.get(f"{base}/api/players")
    async def list_players():
        """Return all registered players."""
        players = container.player_repository.find_all()
        return [{"id": str(p.id.value), "name": p.name} for p in players]


def _register_meetup_routes(app: FastAPI, container: "Container", prefix: str) -> None:
    """Register meetup-related routes."""
    base = f"/{prefix}" if prefix else ""

    @app.get(f"{base}/api/meetup/active")
    async def meetup_active():
        """Return the current active meetup with or without teams, or 404."""
        return _build_meetup_active_response(container)

    @app.post(f"{base}/api/meetup/parse-callup")
    async def parse_callup(body: ParseCallupInput):
        """Parse a WhatsApp callup text and fuzzy-match player names."""
        players = container.player_repository.find_all()
        result = ParseCallupText().execute(body.text, players)
        date_str = _parse_callup_date(body.text, container.default_hour)

        return {
            "titulars": [_serialise_match(m) for m in result.titulars],
            "reserves": [_serialise_match(m) for m in result.reserves],
            "date": date_str,
        }

    @app.post(f"{base}/api/meetup/create-with-teams")
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

        _upsert_meetup_with_players(container, meetup_date, body.player_ids, existing)

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
        colors = container.team_colors
        emojis = container.team_emojis
        team_a = [player_names[str(pid.value)] for pid in saved_meetup.teams[0].players]
        team_b = [player_names[str(pid.value)] for pid in saved_meetup.teams[1].players]

        return {
            "team_a": team_a,
            "team_b": team_b,
            "name_a": colors[0].capitalize(),
            "name_b": colors[1].capitalize(),
            "emoji_a": emojis[0],
            "emoji_b": emojis[1],
            "match_url": match_url,
        }

    @app.post(f"{base}/api/meetup/assign-teams")
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

        return _build_meetup_active_response(container)


# ── Private helpers ───────────────────────────────────────────────────────────


def _upsert_meetup_with_players(
    container: "Container",
    meetup_date: datetime,
    player_ids: list[str],
    existing: "Meetup | None",
) -> None:
    """Create or reset a meetup and assign the given player IDs to it."""
    if existing:
        existing.players.clear()
        existing.clear_teams()
        for pid_str in player_ids:
            existing.add_player(PlayerId.from_string(pid_str))
        container.meetup_repository.save(existing)
    else:
        meetup = container.create_meetup().execute(meetup_date)
        for pid_str in player_ids:
            meetup.add_player(PlayerId.from_string(pid_str))
        container.meetup_repository.save(meetup)


def _build_active_match_response(container: "Container") -> dict:
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

    team_a = _sorted_names(meetup.teams[0].players, player_names)
    team_b = _sorted_names(meetup.teams[1].players, player_names)

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


def _build_meetup_active_response(container: "Container") -> dict:
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

    team_a = _sorted_names(meetup.teams[0].players, player_names)
    team_b = _sorted_names(meetup.teams[1].players, player_names)

    match_url = container.start_match().execute(meetup.date)

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


def _handle_match_events(container: "Container", date: str) -> dict:
    """Load events of a closed match with player IDs resolved to names."""
    try:
        meetup_date = datetime.fromisoformat(date)
    except ValueError as exc:
        raise HTTPException(422, "Invalid date format") from exc

    meetup = container.meetup_repository.find_by_datetime(meetup_date)
    if meetup is None:
        raise HTTPException(404, "Meetup not found")
    if not meetup.is_closed():
        raise HTTPException(409, "Match is not closed yet")
    if meetup.teams is None:
        raise HTTPException(409, "Match has no teams")
    if meetup.result is None:  # pragma: no cover — implied by is_closed()
        raise HTTPException(409, "Match has no result")

    all_players = container.player_repository.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    colors = container.team_colors
    hex_bg = container.team_hex_bg
    hex_text = container.team_hex_text

    team_a = _sorted_names(meetup.teams[0].players, player_names)
    team_b = _sorted_names(meetup.teams[1].players, player_names)

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


async def _handle_edit_match(
    container: "Container",
    notifier: "MatchNotifier",
    date: str,
    body: FinishMatchInput,
) -> dict:
    """Replace result of a closed match and re-fire the notification."""
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

    await notifier.on_match_closed(updated)

    return {
        "meetup_date": date,
        "score_a": updated.result.score_a,
        "score_b": updated.result.score_b,
    }


def _sorted_names(player_ids, player_names: dict[str, str]) -> list[str]:
    """Return locale-sorted display names for a list of player IDs."""
    _sort = functools.cmp_to_key(locale.strcoll)
    return sorted(
        [player_names.get(str(pid.value), "(desconocido)") for pid in player_ids],
        key=_sort,
    )


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


def _parse_callup_date(text: str, default_hour: str) -> str:
    """Extract the meetup date from a callup header line using locale-aware strptime.

    Tries each line as '%A %d %B' (e.g. 'lunes 18 mayo'). Falls back to today
    when no line matches. If the parsed date is more than 7 days in the past,
    bumps to the next year.

    Returns an ISO 8601 string 'YYYY-MM-DDTHH:MM'.
    """
    try:
        hour, minute = (int(p) for p in default_hour.split(":", 1))
    except ValueError:
        hour, minute = 20, 0
    today = datetime.now()
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            parsed = datetime.strptime(" ".join(parts[:3]).lower(), "%A %d %B")
        except ValueError:
            continue
        candidate = datetime(today.year, parsed.month, parsed.day, hour, minute)
        if candidate < today - timedelta(days=7):
            candidate = candidate.replace(year=today.year + 1)
        return candidate.strftime("%Y-%m-%dT%H:%M")
    return datetime(today.year, today.month, today.day, hour, minute).strftime("%Y-%m-%dT%H:%M")
