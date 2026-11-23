"""Client for PyBall's plugin API (/api/v1) and its event stream."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, AsyncIterable, AsyncIterator, Generic, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter

Out = TypeVar("Out")


@dataclass(frozen=True)
class Endpoint(Generic[Out]):
    """One PyBall call: its method, its path and the type it answers with.

    A plugin declares every call it makes once, as an Endpoint, and sends requests only
    through them; its contract test checks each one against ``plugins/openapi.json``.

    ``out`` is any type pydantic validates (a model, ``list[Model]``, ...), or ``bytes``
    for a binary answer. ``sample`` is the JSON body the plugin sends, as the contract
    test sends it; None sends none. ``query`` names the query parameters it passes.
    """

    method: str
    path: str
    out: Any
    sample: BaseModel | None = None
    query: tuple[str, ...] = field(default=())

    def url(self, path_params: dict[str, str]) -> str:
        """Return the path with its ``{name}`` placeholders filled in."""
        return self.path.format(**path_params)

    def decode(self, response: httpx.Response) -> Out:
        """Decode a successful answer as ``out``."""
        if self.out is bytes:
            return response.content  # type: ignore[return-value]
        return self.adapter.validate_python(response.json())

    @cached_property
    def adapter(self) -> TypeAdapter[Out]:
        """Return the pydantic adapter for ``out``."""
        return TypeAdapter(self.out)


class ApiError(Exception):
    """PyBall refused a call or could not be reached."""

    def __init__(self, message: str, status: int | None = None) -> None:
        """Keep the HTTP status, None when PyBall could not be reached."""
        super().__init__(message)
        self.status = status


class Api:
    """The plugin API at ``base_url``, called with the plugin's bearer ``token``."""

    def __init__(
        self, base_url: str, token: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        """Build the HTTP client; ``transport`` replaces the network in tests."""
        self._base = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(60, connect=10),  # team generation can be slowish
            transport=transport,
        )

    async def aclose(self) -> None:
        """Close the connections."""
        await self._http.aclose()

    async def call(
        self,
        endpoint: Endpoint[Out],
        body: BaseModel | None = None,
        params: dict[str, str] | None = None,
        **path_params: str,
    ) -> Out:
        """Call ``endpoint`` and decode its answer; any error status raises ApiError."""
        response = await self._request(endpoint, body, params, path_params)
        return endpoint.decode(_checked(response, endpoint, path_params))

    async def call_optional(
        self,
        endpoint: Endpoint[Out],
        params: dict[str, str] | None = None,
        **path_params: str,
    ) -> Out | None:
        """Call a bodyless ``endpoint``; None when PyBall answers 404."""
        response = await self._request(endpoint, None, params, path_params)
        if response.status_code == 404:
            return None
        return endpoint.decode(_checked(response, endpoint, path_params))

    async def events(
        self, endpoint: Endpoint[Out], last_event_id: int | None
    ) -> AsyncIterator[Out]:
        """Yield the events after ``last_event_id`` (only new ones if None), then live ones.

        Ends when PyBall closes the stream. An idle stream sends a keepalive every 15 s,
        so one silent for a minute is dead and raises ApiError, like an unreachable PyBall.
        """
        headers = {"Accept": "text/event-stream"}
        if last_event_id is not None:
            headers["Last-Event-ID"] = str(last_event_id)
        try:
            async with self._http.stream(
                endpoint.method,
                endpoint.path,
                headers=headers,
                timeout=httpx.Timeout(60, connect=10),
            ) as response:
                if response.is_error:
                    await response.aread()
                    _checked(response, endpoint, {})
                async for data in sse_data(response.aiter_lines()):
                    yield endpoint.adapter.validate_json(data)
        except httpx.TransportError as exc:
            raise ApiError(f"cannot reach PyBall at {self._base}: {exc}") from exc

    async def _request(
        self,
        endpoint: Endpoint[Out],
        body: BaseModel | None,
        params: dict[str, str] | None,
        path_params: dict[str, str],
    ) -> httpx.Response:
        try:
            return await self._http.request(
                endpoint.method,
                endpoint.url(path_params),
                json=body.model_dump(mode="json") if body is not None else None,
                params=params,
            )
        except httpx.TransportError as exc:
            raise ApiError(f"cannot reach PyBall at {self._base}: {exc}") from exc


async def sse_data(lines: AsyncIterable[str]) -> AsyncIterator[str]:
    """Yield the data of each server-sent event in ``lines``, skipping comments."""
    data: list[str] = []
    async for line in lines:
        if not line:
            if data:
                yield "\n".join(data)
                data = []
        elif line.startswith("data:"):
            chunk = line[len("data:") :]
            data.append(chunk[1:] if chunk.startswith(" ") else chunk)


def _checked(
    response: httpx.Response, endpoint: Endpoint[Any], path_params: dict[str, str]
) -> httpx.Response:
    """Return ``response`` if it succeeded, else raise ApiError naming the call."""
    if response.is_success:
        return response
    what = f"{endpoint.method} {endpoint.url(path_params)}"
    try:
        detail = json.dumps(response.json().get("detail", ""), ensure_ascii=False)
    except (ValueError, AttributeError):
        detail = ""
    hint = (
        " — check PYBALL_API_TOKEN and the plugin's scopes"
        if response.status_code in (401, 403)
        else ""
    )
    raise ApiError(f"{what}: {response.status_code} {detail}{hint}", response.status_code)
