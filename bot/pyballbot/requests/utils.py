from dataclasses import dataclass
from enum import Enum
from typing import Optional

import requests

from pyballbot.requests.types import Response
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.settings import PYBALL_API_URL


class BaseEndpoint(Enum):
    PLAYER = f"{PYBALL_API_URL}/player"
    MEETUP = f"{PYBALL_API_URL}/meetup"


class RequestType(Enum):
    GET = requests.get
    POST = requests.post
    PUT = requests.put



def get_json_response(
    request_type: RequestType, endpoint: BaseEndpoint, route: str, json: Optional[dict] = None
) -> Response:
    response_json = None
    try:
        response: requests.Response = request_type(f"{endpoint.value}/{route}", json=json)
    except requests.exceptions.ConnectionError as error:
        raise CouldNotConnectToTheCore(f"Core is not available: {error}")

    if response.status_code not in (204, 304):
        response_json = response.json()

    return Response(status_code=response.status_code, json=response_json)
