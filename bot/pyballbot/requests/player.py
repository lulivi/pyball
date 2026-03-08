import logging
import uuid

from typing import Dict, List, Optional, Union, cast

from pyballbot import player_telegram_id_translator as translator
from pyballbot.logger import log_func
from pyballbot.requests.errors import (
    PlayerCreationError,
    PlayerIdDoesNotExist,
    PlayerNameDoesNotExist,
    PlayerNameIsAlreadyInUse,
    PlayerQueryError,
    PlayerUpdateError,
)
from pyballbot.requests.types import Player, Response
from pyballbot.requests.utils import BaseEndpoint, RequestMethod, get_response

logger = logging.getLogger(__name__)


@log_func
def get_all() -> List[Player]:
    return cast(List[Player], _get())


@log_func
def get_by(**kwargs) -> Player:
    if len(kwargs) != 1:
        raise PlayerQueryError(
            "None or more than one element where specified in the single query call"
        )

    return cast(Player, _get(**kwargs))


@log_func
def _get(
    id: Optional[uuid.UUID] = None, name: Optional[str] = None
) -> Union[Player, List[Player]]:
    response: Response = get_response(
        request_method=RequestMethod.GET,
        base_endpoint=BaseEndpoint.PLAYERS,
        params=get_params(id=id, name=name),
    )

    if response.status != 200:
        if response.status == 404:
            if id is not None:
                raise PlayerIdDoesNotExist(id=id)
            raise PlayerNameDoesNotExist(name=name)
        raise PlayerQueryError(response.json["error"]["message"])

    if isinstance(response.json, list):
        return [Player.from_json(json_player) for json_player in response.json]

    return Player.from_json(response.json)


def get_params(id: Optional[uuid.UUID], name: Optional[str] = None) -> Optional[Dict[str, str]]:
    if id is not None:
        return {"id": str(id)}

    if name is not None:
        return {"name": name}

    return None


@log_func
def create(name: str, telegram_id: str, main: bool) -> None:
    response: Response = get_response(
        request_method=RequestMethod.POST,
        base_endpoint=BaseEndpoint.PLAYERS,
        route="",
        json={"name": name, "main": main},
    )

    if response.status != 201:
        if response.status == 409:
            raise PlayerNameIsAlreadyInUse(name=name)
        logger.error(">>>>>>>>>> json response", response.json)
        raise PlayerCreationError(response.json["message"])

    player_id: uuid.UUID = response.json["id"]

    try:
        translator.PlayerToTelegramIdTranslatorService().save(
            id=player_id, telegram_id=telegram_id
        )
    except translator.PlayerTelegramIdAlreadyInUse as error:
        conflicted_player_id: (
            uuid.UUID
        ) = translator.PlayerToTelegramIdTranslatorService().translate_telegram_id(
            telegram_id=telegram_id
        )

        try:
            player: Player = get_by(id=conflicted_player_id)
        except PlayerIdDoesNotExist as error:
            raise PlayerCreationError(
                f"The Telegram ID `{telegram_id}` is already bounded to a player that does not"
                " exist anymore. Please, manually remove the player from the translator."
            ) from error

        raise PlayerCreationError(
            f"The Telegram ID `{telegram_id}` is already bounded to the player `{player.name}`."
            " Please, manually set the player Telegram ID or change the other's player Telegram"
            " ID before."
        )


@log_func
def rename(current_name: str, new_name: str) -> None:
    player: Player = get_by(name=current_name)

    response: Response = get_response(
        request_method=RequestMethod.PUT,
        base_endpoint=BaseEndpoint.PLAYERS,
        json={"id": player.id, "name": new_name, "main": player.main},
    )

    if response.status != 204:
        if response.status == 404:
            raise PlayerIdDoesNotExist(id=player.id)
        raise PlayerUpdateError(
            f"Could not update the player `{player.id}`: {response.json['message']}"
        )
