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

from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.infrastructure.http.schemas import CreatePlayerInput

if TYPE_CHECKING:
    from pyball.application.container import Container


def register_player_routes(app: FastAPI, container: "Container") -> None:
    """Register player-related routes."""

    @app.get("/api/players")
    async def list_players():
        """Return all registered players."""
        players = container.player_repository.find_all()
        return [{"id": str(p.id.value), "name": p.name} for p in players]

    @app.post("/api/players", status_code=201)
    async def create_player_endpoint(body: CreatePlayerInput):
        """Create a new substitute player, or 409 if the name already exists."""
        name = body.name.strip()
        if not name:
            raise HTTPException(422, "Name cannot be empty")
        try:
            player = container.create_player().execute(name=name, group="substitute")
        except PlayerAlreadyExistsError as exc:
            raise HTTPException(409, f"A player named {name!r} already exists") from exc
        return {"id": str(player.id.value), "name": player.name}
