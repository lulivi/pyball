import uuid

from typing import List

import requests

from pyballbot import player_telegram_uuid_translator as translator
from pyballbot.requests.errors import (
    PlayerCreationError,
    PlayerNameDoesNotExist,
    PlayerNameIsAlreadyInUse,
    PlayerQueryError,
)
from pyballbot.requests.types import Player, Response
from pyballbot.requests.utils import BaseEndpoint, RequestMethod, get_response


def create(name: str, telegram_id: str) -> None:
    try:
        response: Response = get_response(
            request_method=RequestMethod.POST,
            base_endpoint=BaseEndpoint.PLAYERS,
            route="",
            json={"name": name},
        )
        if "id" not in response.json:
            raise PlayerCreationError("Could not find the new player ID in the response")
        player_id: uuid.UUID = response.json["id"]
    except requests.exceptions.HTTPError as error:
        error_response = error.response.json()["detail"]["error"]
        if error.errno == 409 and error_response["value"] == "name":
            raise PlayerNameIsAlreadyInUse(name=name) from error
        raise PlayerCreationError(
            f"Unknown error creating the player: {error_response['message']}"
        )

    try:
        translator.TelegramPlayerTranslatorService().save(id=player_id, telegram_id=telegram_id)
    except translator.PlayerIdAlreadyInUse as error:
        # Remove player endpoint ????
        raise error
    except translator.PlayerTelegramIdAlreadyInUse as error:
        # Remove player endpoint ????
        raise error


def get_all() -> List[Player]:
    try:
        return [
            Player.from_json(json_player)
            for json_player in get_response(
                request_method=RequestMethod.GET,
                base_endpoint=BaseEndpoint.PLAYERS,
                route="",
                params=None,
            ).json
        ]

    except requests.exceptions.HTTPError as error:
        if error.errno == 404:
            raise PlayerNameDoesNotExist(name=name)
        raise PlayerQueryError(f"Unknown error: {error.strerror}")


def get_by_name(name: str) -> Player:
    try:
        return Player.from_json(
            get_response(
                request_method=RequestMethod.GET,
                base_endpoint=BaseEndpoint.PLAYERS,
                route=f"",
                params={"name": name},
            ).json
        )
    except requests.exceptions.HTTPError as error:
        if error.errno == 404:
            raise PlayerNameDoesNotExist(name=name)
        raise PlayerQueryError(f"Unknown error: {error.strerror}")
