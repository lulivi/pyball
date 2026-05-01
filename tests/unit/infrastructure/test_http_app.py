"""Tests for the FastAPI HTTP application."""
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.errors import MeetupAlreadyClosedError
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.infrastructure.http.app import create_app


class _StubNotifier(MatchNotifier):
    """In-memory notifier for testing."""

    def __init__(self):
        self.closed = []

    async def on_match_closed(self, meetup):
        self.closed.append(meetup)

    async def on_meetup_updated(self, meetup):
        pass


def _make_app(finish_side_effect=None, finish_return=None):
    container = MagicMock()
    notifier = _StubNotifier()
    if finish_side_effect:
        container.finish_match.return_value.execute.side_effect = finish_side_effect
    elif finish_return is not None:
        container.finish_match.return_value.execute.return_value = finish_return
    return create_app(container, notifier), notifier


_VALID_BODY = {
    "meetup_date": "2026-04-30",
    "events": [],
    "finalScore": {"A": 2, "B": 1},
}


@pytest.mark.asyncio
async def test_finish_match_success_calls_notifier():
    meetup = MagicMock()
    meetup.result.score_a = 2
    meetup.result.score_b = 1
    app, notifier = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 200
    assert len(notifier.closed) == 1
    assert notifier.closed[0] is meetup


@pytest.mark.asyncio
async def test_finish_match_success_returns_score():
    meetup = MagicMock()
    meetup.result.score_a = 2
    meetup.result.score_b = 1
    app, _ = _make_app(finish_return=meetup)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.json() == {
        "meetup_date": "2026-04-30",
        "score_a": 2,
        "score_b": 1,
    }


@pytest.mark.asyncio
async def test_finish_match_404_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=MeetupNotFoundError("2026-04-30"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 404
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_finish_match_409_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=MeetupAlreadyClosedError("closed"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 409
    assert len(notifier.closed) == 0


@pytest.mark.asyncio
async def test_finish_match_422_does_not_call_notifier():
    app, notifier = _make_app(finish_side_effect=ValueError("bad date"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/match/finish", json=_VALID_BODY)

    assert response.status_code == 422
    assert len(notifier.closed) == 0
