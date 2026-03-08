import asyncio
import functools
import json
import threading

from collections import defaultdict
from typing import Callable, Dict, List

from websockets import serve
from websockets.asyncio.client import connect


class EventBus:
    async def __init__(self, listen_uri: str, bus_uri: str) -> None:
        self._event_mapper: Dict[str, List[Callable]] = defaultdict(lambda: [])
        self._listen_uri = listen_uri
        self._bus_uri = bus_uri

        asyncio.get_event_loop().run_until_complete(self._handshake())

        print("The token is:", self._token)

        self._listener_task = asyncio.create_task(self.start_listener())

    async def _handshake(self):
        async with connect(self._bus_uri) as websocket:
            await websocket.send(f"GET_TOKEN {self._listen_uri}")
            self._token = await websocket.recv()

    async def subscribe(self, func: Callable, event_name: str) -> None:
        async with connect(self._bus_uri) as websocket:
            await websocket.send(f"SUBSCRIBE {self._token} {event_name}")

        self._event_mapper[event_name].append(func)

    async def emit(self, event_name: str, event: dict) -> None:
        encoded_event: str = json.dumps(event)

        async with connect(self._bus_uri) as websocket:
            await websocket.send(f"EMIT {event_name} {encoded_event}")

    def on(self, event_name: str):
        def decorator(function):
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                self.subscribe(func=function, event_name=event_name)

            return wrapper

        return decorator

    async def _listen_loop(self, websocket):
        new_event: str = await websocket.recv()
        event_name, content = new_event.split(" ", 1)

        if event_name in self._event_mapper:
            self._event_mapper[event_name](json.loads(content))

    async def start_listener(self):
        async with serve(self._listen_loop, "localhost", self._listen_uri):
            await asyncio.get_running_loop().create_future()
