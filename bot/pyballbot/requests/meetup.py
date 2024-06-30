import datetime
import uuid

from typing import List, Tuple

import requests

from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import (
    AddPlayerToMeetupError,
    MeetupCreationError,
    MeetupDateTimeIsAlreadyInUse,
    MeetupIdDoesNotExist,
    PlayerIdDoesNotExist,
    PlayerIsAreadyCalled,
)
from pyballbot.requests.types import Meetup, Player, Response
from pyballbot.requests.utils import BaseEndpoint, RequestType, get_json_response
from pyballbot.settings import PYBALL_API_URL


def create(
    date_time: datetime.datetime,
    location: str,
    possible_team_sizes: Tuple[int, ...],
):
    try:
        with requests.post(
            f"{PYBALL_API_URL}/meetup/create",
            json={
                "date_time": date_time.isoformat(),
                "location": location,
                "possible_team_sizes": possible_team_sizes,
            },
        ) as response:
            if "id" not in response.json():
                raise MeetupCreationError("Could not find the new meetup ID in the response")
    except requests.exceptions.HTTPError as error:
        error_response = error.response.json()["detail"]["error"]
        if error.errno == 404 and error_response["value"] == "date_time":
            raise MeetupDateTimeIsAlreadyInUse(date_time=date_time) from error
        raise MeetupCreationError(
            f"Unknown error creating the meetup: {error_response['message']}"
        )


def add_player_by_name(
    meetup_id: uuid.UUID,
    player_name: str,
):
    player: Player = player_requests.get_by_name(player_name)
    add_player(meetup_id=meetup_id, player_id=player.id)


def add_player(meetup_id: uuid.UUID, player_id: uuid.UUID):
    try:
        response: Response = get_json_response(
            request_type=RequestType.PUT,
            endpoint=BaseEndpoint.MEETUP,
            route=f"{str(meetup_id)}/add_player",
            json={"player_id": player_id},
        )
    except requests.exceptions.HTTPError as error:
        error_response = error.response.json()["detail"]["error"]
        if error.errno == 404:
            if error_response["value"] == "player_id":
                raise PlayerIdDoesNotExist(id=player_id)
            raise MeetupIdDoesNotExist(id=meetup_id)
        raise AddPlayerToMeetupError(
            f"Unknown error when trying to add player to meetup: {error.strerror}"
        )

    if response.status_code == 304:
        raise PlayerIsAreadyCalled(meetup_id=meetup_id, player_id=player_id)


def get_all() -> List[Meetup]:
    meetups = [
        Meetup.from_json(meetup_json)
        for meetup_json in get_json_response(
            request_type=RequestType.GET,
            endpoint=BaseEndpoint.MEETUP,
            route="all",
        ).json
    ]

    return meetups
