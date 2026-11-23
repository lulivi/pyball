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

"""A fake PyBall core and a fake Telegram bot for the plugin's tests."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pyball_client import Api

from pyball_telegram.api import Meetup, Settings
from pyball_telegram.callups import Callups
from pyball_telegram.config import Chat, Config

DATE = datetime(2026, 11, 25, 20, 0)
LUIS = "11111111-1111-4111-8111-111111111111"
SUB = "22222222-2222-4222-8222-222222222222"
PLAYERS = [
    {"id": LUIS, "name": "Luis", "group": "regular", "position": None},
    {"id": SUB, "name": "Manu", "group": "substitute", "position": None},
]


def meetup(**changes: Any) -> dict[str, Any]:
    """A meetup as the API answers it, open with Luis signed up."""
    base: dict[str, Any] = {
        "id": "m1",
        "date": DATE.isoformat(),
        "location": "Campo",
        "capacity": 10,
        "substitute_search": False,
        "players": [LUIS],
        "teams": None,
        "matches": [],
        "closed": False,
    }
    return base | changes


class FakeCore:
    """Answers the plugin API from ``routes``: ``(method, path) -> JSON or bytes``."""

    def __init__(self) -> None:
        """Start with the players and no meetup."""
        self.routes: dict[tuple[str, str], Any] = {("GET", "/api/v1/players"): PLAYERS}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        """Answer one request."""
        key = (request.method, request.url.path)
        self.calls.append((request.method, str(request.url).removeprefix("http://core")))
        if key not in self.routes:
            return httpx.Response(404, json={"detail": "Not found"})
        answer = self.routes[key]
        if isinstance(answer, bytes):
            return httpx.Response(200, content=answer)
        return httpx.Response(200, json=answer)


@pytest.fixture
def core() -> FakeCore:
    """The fake core."""
    return FakeCore()


@pytest.fixture
def bot() -> MagicMock:
    """A bot whose sends answer message 100."""
    fake = MagicMock()
    fake.send_message = AsyncMock(return_value=MagicMock(message_id=100))
    fake.edit_message_text = AsyncMock()
    fake.send_photo = AsyncMock()
    fake.set_message_reaction = AsyncMock()
    return fake


@pytest.fixture
def callups(core, bot, tmp_path) -> Callups:
    """Callups over the fake core and bot, with every chat configured."""
    config = Config(
        bot_token="t",
        admins_ids=frozenset({1}),
        regulars_meetups=Chat(-10, 5),
        substitutes_meetups=Chat(-20),
        regulars_stats=Chat(-30, 7),
        data_dir=tmp_path,
    )
    api = Api("http://core/api/v1", "tok", transport=httpx.MockTransport(core))
    settings = Settings(display_date_format="%Y-%m-%d %H:%M", locale="C")
    return Callups(bot, api, config, settings)


def parse(raw: dict[str, Any]) -> Meetup:
    """Decode a meetup as the plugin does."""
    return Meetup.model_validate(raw)
