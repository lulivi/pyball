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
"""Signup route registrar and handlers — the /signup page and /api/signup/*."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from pyball.domain.meetup.errors import (
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    SignupClosedError,
)
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.http.presenters import build_signup_meetup_response
from pyball.infrastructure.http.schemas import ChangeCodeInput, VerifyCodeInput
from pyball.infrastructure.signup.code_store import SignupCodeStore

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.domain.meetup.models import Meetup

_IDENTITY_COOKIE = "pyball_signup_player"


def register_signup_routes(
    app: FastAPI, container: "Container", signup_token: str, static_dir: Path
) -> None:
    """Register the /signup page and /api/signup/* routes."""

    @app.get("/signup")
    async def signup_page():
        """Serve the signup SPA."""
        content = (static_dir / "signup.html").read_text()
        return HTMLResponse(content)

    @app.post("/api/signup/verify")
    async def verify_code_endpoint(request: Request, body: VerifyCodeInput):
        """Validate a personal code, identify the player, and set the identity cookie."""
        store = _code_store(container)
        player_id_str = store.verify_code(body.code)
        player = _player_or_none(container, player_id_str)
        if player is None:
            raise HTTPException(401, "Código incorrecto")
        identified_id = str(player.id.value)
        response = JSONResponse({"id": identified_id, "name": player.name})
        _set_identity_cookie(
            response, identified_id, signup_token, secure=request.url.scheme == "https"
        )
        return response

    @app.get("/api/signup/me")
    async def get_me_endpoint(request: Request):
        """Return the currently identified player, or 401."""
        player_id = _require_identity(request, container, signup_token)
        player = container.player_repository.find_by_id(player_id)
        if player is None:
            raise HTTPException(401, "No identificado")
        return {"id": str(player_id.value), "name": player.name}

    @app.post("/api/signup/logout")
    async def logout_endpoint():
        """Clear the identity cookie (e.g. to hand off a shared device)."""
        response = JSONResponse({"status": "logged_out"})
        response.delete_cookie(_IDENTITY_COOKIE, path="/")
        return response

    @app.post("/api/signup/change-code")
    async def change_code_endpoint(request: Request, body: ChangeCodeInput):
        """Change the identified player's own code, after verifying the current one."""
        player_id = _require_identity(request, container, signup_token)
        store = _code_store(container)
        matched = store.verify_code(body.current_code)
        if matched is None or matched != str(player_id.value):
            raise HTTPException(401, "Código actual incorrecto")
        store.set_code(str(player_id.value), body.new_code)
        return {"status": "changed"}

    @app.get("/api/signup/meetup")
    async def signup_meetup_endpoint(request: Request):
        """Return the next meetup's state, scoped to the identified player."""
        player_id = _require_identity(request, container, signup_token)
        return build_signup_meetup_response(container, player_id)

    @app.post("/api/signup/join")
    async def join_endpoint(request: Request):
        """Join the active meetup as the identified player."""
        player_id = _require_identity(request, container, signup_token)
        meetup = _active_meetup_or_404(container)
        try:
            container.add_player_to_meetup_by_id().execute(meetup.date, player_id)
        except SignupClosedError as exc:
            raise HTTPException(409, str(exc)) from exc
        return build_signup_meetup_response(container, player_id)

    @app.post("/api/signup/leave")
    async def leave_endpoint(request: Request):
        """Leave the active meetup as the identified player."""
        player_id = _require_identity(request, container, signup_token)
        meetup = _active_meetup_or_404(container)
        try:
            container.remove_player_from_meetup_by_id().execute(meetup.date, player_id)
        except (SignupClosedError, PlayerNotInMeetupError) as exc:
            raise HTTPException(409, str(exc)) from exc
        return build_signup_meetup_response(container, player_id)


# ── Private helpers ───────────────────────────────────────────────────────────


def _code_store(container: "Container") -> SignupCodeStore:
    """Build a SignupCodeStore rooted at this instance's data directory."""
    return SignupCodeStore(container.data_dir / "signup" / "codes.json")


def _player_or_none(container: "Container", player_id_str: str | None):
    """Look up a player by ID string, returning None if not found or ID is None."""
    if player_id_str is None:
        return None
    try:
        player_id = PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError:
        return None
    return container.player_repository.find_by_id(player_id)


def _active_meetup_or_404(container: "Container") -> "Meetup":
    """Return the active meetup, or raise 404."""
    try:
        return container.get_active_meetup().execute()
    except MeetupNotFoundError as exc:
        raise HTTPException(404, "No hay convocatoria activa") from exc


def _set_identity_cookie(
    response: JSONResponse, player_id: str, signup_token: str, secure: bool
) -> None:
    """Set the HMAC-signed identity cookie on the response."""
    mac = hmac.new(signup_token.encode(), player_id.encode(), hashlib.sha256).hexdigest()
    response.set_cookie(
        _IDENTITY_COOKIE,
        f"{player_id}.{mac}",
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=31536000,
        path="/",
    )


def _require_identity(request: Request, container: "Container", signup_token: str) -> PlayerId:
    """Return the identified player's ID from the cookie, or raise 401."""
    raw = request.cookies.get(_IDENTITY_COOKIE)
    if not raw or "." not in raw:
        raise HTTPException(401, "No identificado")
    player_id_str, _, mac = raw.partition(".")
    expected = hmac.new(signup_token.encode(), player_id_str.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        raise HTTPException(401, "No identificado")
    try:
        player_id = PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError as exc:
        raise HTTPException(401, "No identificado") from exc
    if container.player_repository.find_by_id(player_id) is None:
        raise HTTPException(401, "No identificado")
    return player_id
