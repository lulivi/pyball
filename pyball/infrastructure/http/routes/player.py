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
"""Player route registrar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException

from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
from pyball.domain.player.models import VALID_POSITIONS, PlayerId
from pyball.infrastructure.http.schemas import CreatePlayerInput, EditPlayerInput
from pyball.infrastructure.signup.code_store import SignupCodeStore, generate_code

if TYPE_CHECKING:
    from pyball.application.container import Container


def register_player_routes(  # pylint: disable=too-many-statements
    app: FastAPI, container: "Container", enable_web_signup: bool = False
) -> None:
    """Register player-related routes."""

    @app.get("/api/players")
    async def list_players():
        """Return all registered players."""
        players = container.player_repository.find_all()
        if not enable_web_signup:
            return [
                {"id": str(p.id.value), "name": p.name, "group": p.group, "position": p.position}
                for p in players
            ]
        store = _code_store(container)
        return [
            {
                "id": str(p.id.value),
                "name": p.name,
                "group": p.group,
                "position": p.position,
                "has_signup_code": store.has_code(str(p.id.value)),
            }
            for p in players
        ]

    @app.post("/api/players", status_code=201)
    async def create_player_endpoint(body: CreatePlayerInput):
        """Create a new player, or 409 if the name already exists."""
        name = body.name.strip()
        if not name:
            raise HTTPException(422, "Name cannot be empty")
        if body.group not in ("regular", "substitute"):
            raise HTTPException(422, "Group must be 'regular' or 'substitute'")
        if body.position is not None and body.position not in VALID_POSITIONS:
            raise HTTPException(422, f"Invalid position: {body.position!r}")
        try:
            player = container.create_player().execute(
                name=name, group=body.group, position=body.position
            )
        except PlayerAlreadyExistsError as exc:
            raise HTTPException(409, f"A player named {name!r} already exists") from exc
        response = {
            "id": str(player.id.value),
            "name": player.name,
            "group": player.group,
            "position": player.position,
        }
        if enable_web_signup:
            code = generate_code()
            _code_store(container).set_code(str(player.id.value), code)
            response["signup_code"] = code
        return response

    @app.post("/api/players/{player_id}/edit")
    async def edit_player_endpoint(player_id: str, body: EditPlayerInput):
        """Rename a player and update their group and position."""
        name = body.name.strip()
        if not name:
            raise HTTPException(422, "Name cannot be empty")
        if body.group not in ("regular", "substitute"):
            raise HTTPException(422, "Group must be 'regular' or 'substitute'")
        if body.position is not None and body.position not in VALID_POSITIONS:
            raise HTTPException(422, f"Invalid position: {body.position!r}")
        try:
            container.rename_player().execute(player_id, name)
            container.change_player_group().execute(player_id, body.group)
            player = container.set_player_position().execute(player_id, body.position)
        except PlayerNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except NameAlreadyTakenError as exc:
            raise HTTPException(409, str(exc)) from exc
        except InvalidPlayerIdError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "id": str(player.id.value),
            "name": player.name,
            "group": player.group,
            "position": player.position,
        }

    @app.delete("/api/players/{player_id}")
    async def delete_player_endpoint(player_id: str):
        """Delete a player by ID."""
        try:
            container.delete_player().execute(player_id)
        except PlayerNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except InvalidPlayerIdError as exc:
            raise HTTPException(422, str(exc)) from exc
        if enable_web_signup:
            _code_store(container).delete_code(str(PlayerId.from_string(player_id).value))
        return {"status": "deleted", "id": player_id}

    @app.post("/api/players/{player_id}/signup-code/regenerate")
    async def regenerate_signup_code_endpoint(player_id: str):
        """Generate and store a new signup code, returning it once in plaintext."""
        if not enable_web_signup:
            raise HTTPException(404, "Not Found")
        try:
            parsed_id = PlayerId.from_string(player_id)
        except InvalidPlayerIdError as exc:
            raise HTTPException(422, str(exc)) from exc
        if container.player_repository.find_by_id(parsed_id) is None:
            raise HTTPException(404, f"Player with id '{player_id}' not found")
        code = generate_code()
        _code_store(container).set_code(str(parsed_id.value), code)
        return {"code": code}


# ── Private helpers ───────────────────────────────────────────────────────────


def _code_store(container: "Container") -> SignupCodeStore:
    """Build a SignupCodeStore rooted at this instance's data directory."""
    return SignupCodeStore(container.data_dir / "signup" / "codes.json")
