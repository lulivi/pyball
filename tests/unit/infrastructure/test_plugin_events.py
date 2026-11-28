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
"""Tests for GET /api/v1/events, driven as raw ASGI to act between its frames."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.plugins.api import create_plugin_api
from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.infrastructure.plugins.event_log import EventLog


@pytest.mark.asyncio
async def test_an_event_written_right_after_the_200_is_delivered(tmp_path):
    """With no position, an event appended as the response starts still arrives."""
    log = EventLog(tmp_path / "events.jsonl", ("blanco", "negro"), ("⚪", "⚫"))
    container = SimpleNamespace(event_log=log)
    api = create_plugin_api(
        cast(Any, container), cast(Any, None), PluginCredentials([], manage_token="tok")
    )
    meetup = Meetup.create(datetime(2026, 11, 25, 20, 0), "Campo")
    body = b""

    async def receive() -> dict:
        await asyncio.Event().wait()  # the client never goes away
        return {}

    async def send(message: dict) -> None:
        nonlocal body
        if message["type"] == "http.response.start":
            log.append("meetup.created", meetup)
        elif message["type"] == "http.response.body":
            body += message.get("body", b"")
            if b"id: 1" in body:
                log.close_subscribers()

    await asyncio.wait_for(api(_events_scope(), receive, send), timeout=5)

    assert b"id: 1" in body


def _events_scope() -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/events",
        "raw_path": b"/events",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer tok")],
        "client": ("test", 1),
        "server": ("test", 80),
    }
