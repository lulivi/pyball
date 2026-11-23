"""Tests for the plugin API client and its event stream."""

import json

import httpx
import pytest
from pydantic import BaseModel

from pyball_client import Api, ApiError, Endpoint


class Meetup(BaseModel):
    """The fields a test plugin reads."""

    id: str


ACTIVE: Endpoint[Meetup] = Endpoint("GET", "/meetups/active", Meetup)
JOIN: Endpoint[Meetup] = Endpoint("PUT", "/meetups/{meetup_id}/players/{player_id}", Meetup)
STATS: Endpoint[bytes] = Endpoint("GET", "/stats.png", bytes, query=("scope",))
EVENTS: Endpoint[Meetup] = Endpoint("GET", "/events", Meetup)


def _api(handler) -> Api:
    return Api("http://pyball/api/v1/", "tok", transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_calls_with_the_token_and_fills_the_path():
    """A call sends the bearer token to the filled-in path and decodes the answer."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.headers["Authorization"]))
        return httpx.Response(200, json={"id": "m1", "extra": 1})

    meetup = await _api(handler).call(JOIN, meetup_id="m1", player_id="p1")

    assert meetup == Meetup(id="m1")
    assert seen == [("PUT", "/api/v1/meetups/m1/players/p1", "Bearer tok")]


@pytest.mark.asyncio
async def test_optional_call_is_none_on_404_and_bytes_stay_bytes():
    """call_optional turns a 404 into None; a bytes endpoint answers its raw content."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/active"):
            return httpx.Response(404, json={"detail": "No active meetup"})
        assert request.url.params["scope"] == "alltime"
        return httpx.Response(200, content=b"\x89PNG")

    api = _api(handler)
    assert await api.call_optional(ACTIVE) is None
    assert await api.call(STATS, params={"scope": "alltime"}) == b"\x89PNG"


@pytest.mark.asyncio
async def test_errors_name_the_call_and_hint_at_the_token():
    """A 403 raises ApiError with the call, the detail and the scopes hint."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "Missing scope meetups:write"})

    with pytest.raises(ApiError) as caught:
        await _api(handler).call(JOIN, meetup_id="m1", player_id="p1")

    assert caught.value.status == 403
    assert "PUT /meetups/m1/players/p1: 403" in str(caught.value)
    assert "scopes" in str(caught.value)


@pytest.mark.asyncio
async def test_unreachable_pyball_is_an_api_error():
    """A connection failure raises ApiError, with no status."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ApiError) as caught:
        await _api(handler).call(ACTIVE)
    assert caught.value.status is None


@pytest.mark.asyncio
async def test_events_resume_after_the_last_id_and_skip_keepalives():
    """The stream sends Last-Event-ID and yields each event's data, not the pings."""
    sent = []
    body = (
        'id: 8\nevent: meetup.updated\ndata: {"id": "a"}\n\n'
        ": ping\n\n"
        'id: 9\nevent: meetup.updated\ndata: {"id":\ndata: "b"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.headers.get("Last-Event-ID"))
        return httpx.Response(200, content=body.encode())

    got = [m.id async for m in _api(handler).events(EVENTS, 7)]

    assert got == ["a", "b"]
    assert sent == ["7"]


@pytest.mark.asyncio
async def test_a_refused_stream_raises():
    """An error status on the event stream raises ApiError."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=json.dumps({"detail": "Unauthorized"}).encode())

    with pytest.raises(ApiError, match="401"):
        async for _ in _api(handler).events(EVENTS, None):
            pass
