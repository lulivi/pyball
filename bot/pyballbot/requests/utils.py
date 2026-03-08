import logging

from enum import Enum
from typing import Optional

import requests

from pyballbot.logger import log_func
from pyballbot.requests.errors import CouldNotConnectToTheCore
from pyballbot.requests.types import Response
from pyballbot.settings import PYBALL_API_URL

logger = logging.getLogger(__name__)


class BaseEndpoint(Enum):
    PLAYERS = f"{PYBALL_API_URL}/players"
    MEETUPS = f"{PYBALL_API_URL}/meetups"
    MATCHES = f"{PYBALL_API_URL}/matches"


class RequestMethod(Enum):
    GET = requests.get
    POST = requests.post
    PUT = requests.put


@log_func
def get_response(
    request_method: RequestMethod,
    base_endpoint: BaseEndpoint,
    route: str = "",
    json: Optional[dict] = None,
    params: Optional[dict] = None,
) -> Response:
    response_json = None
    endpoint = f"{base_endpoint.value}{route}"
    logger.debug(
        f"Sending request `{request_method.__name__}` to `{endpoint}` with params={params} and"
        f" json={json}"
    )

    try:
        response: requests.Response = request_method(endpoint, params=params, json=json)
    except requests.exceptions.ConnectionError as error:
        logger.error("Connection error sending the request")
        raise CouldNotConnectToTheCore(f"Core is not available: {error}")

    logger.debug(f"Response status: {response.status_code}")
    if response.status_code in (204, 304):
        logger.debug("No content response")
    else:
        response_json = response.json()
        logger.debug(f"Response body: {response_json}")

    return Response(status=response.status_code, json=response_json)
