import asyncio
import hashlib

from collections import defaultdict

from websockets import connect
from websockets.asyncio.server import serve

nodes = {}
events = defaultdict(set)


def main():
    asyncio.run(server())


async def server():
    EVENT_BUS_LOC = 1472

    async with serve(reader, "localhost", EVENT_BUS_LOC):
        await asyncio.get_running_loop().create_future()  # run forever


async def reader(websocket):
    new_event: str = await websocket.recv()

    action, content = new_event.split(" ", 1)

    if "GET_TOKEN" == action:
        return await action_get_token(websocket=websocket, uri=content)

    if action == "SUBSCRIBE":
        return await action_subscribe(content=content)

    if action == "EMIT":
        event_name, event = content.split(" ", 1)
        return await action_emit(event_name=event_name, event=event)

    return "Ayuda?"


async def action_get_token(websocket, uri: str) -> None:
    new_token = hashlib.sha256(uri.encode("utf-8")).hexdigest()

    if new_token in nodes:
        _clean_token_subscriptions(new_token)

    nodes[new_token] = uri
    await websocket.send(new_token)
    print(f"Creado token para {uri}")


def _clean_token_subscriptions(token: str):
    for token_list in events.values():
        token_list.remove(token)


async def action_subscribe(content: str) -> None:
    token, event_name = content.split(" ", 1)
    events[event_name].add(token)
    print(f"Suscrito {token} a {event_name}")


async def action_emit(event_name, event) -> None:
    if event_name not in events:
        print(f"No hay suscriptores al evento {event_name}")
        return

    for token in events[event_name]:
        async with connect(nodes[token]) as websocket_send:
            await websocket_send.send(f"{event_name} {event}")
            print(f"Se ha emitido evento {event_name} al token {token}")


if __name__ == "__main__":
    main()
