import logging
import uuid

from typing import Dict, List, Optional, Tuple, Union, cast

from fastapi import APIRouter, HTTPException
from pyball.player.infrastructure.player_json_repository import PlayerJsonRepository
from pydantic import BaseModel

from pyball.logger import log_func
from pyball.player.application.create_player import CreatePlayer
from pyball.player.application.delete_player import DeletePlayer
from pyball.player.application.update_player import UpdatePlayer
from pyball.player.domain import errors as domain_errors
from pyball.player.domain.model.player import Player
from pyball.player.infrastructure.get_player import GetPlayer
from pyball.utils.api_exceptions import (
    PyballClientConflict,
    PyballClientError,
    PyballClientNotFound,
    PyballClientUnprocessableContent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players")


class PlayerModelOnlyId(BaseModel):
    id: uuid.UUID


class PlayerModelNoId(BaseModel):
    name: str
    main: bool = False


class PlayerModelComplete(PlayerModelOnlyId, PlayerModelNoId):
    """"""


@router.get("", response_model=Union[PlayerModelComplete, List[PlayerModelComplete]])
@log_func
def get_player(
    id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
) -> Union[PlayerModelComplete, List[PlayerModelComplete]]:
    player_getter = GetPlayer()

    if id is None and name is None:
        return [
            PlayerModelComplete(
                id=player.id,
                name=player.name,
                main=player.main,
            )
            for player in player_getter.all()
        ]

    player = get_single_player(player_getter=player_getter, id=id, name=name)

    if player is None:
        raise PyballClientNotFound(object="player", **get_error_info(id=id, name=name))

    return PlayerModelComplete(
        id=player.id,
        name=player.name,
        main=player.main,
    )


def get_single_player(
    player_getter: GetPlayer, id: Optional[uuid.UUID] = None, name: Optional[str] = None
) -> Optional[Player]:
    if id is not None:
        return player_getter.by_id(id=id)

    if name is None:
        raise PyballClientUnprocessableContent(
            message="Name is necessary if the ID is not provided",
            item="name",
        )

    return player_getter.by_name(name=name)


def get_error_info(
    id: Optional[uuid.UUID] = None, name: Optional[str] = None
) -> Dict[str, Union[str, uuid.UUID]]:
    if id is not None:
        return {"item": "id", "value": id}

    return {"item": "name", "value": name}


@router.post("", status_code=201)
@log_func
def create_player(args: PlayerModelNoId) -> PlayerModelComplete:
    new_player_id = uuid.uuid4()

    try:
        CreatePlayer(PlayerJsonRepository()).execute(
            id=new_player_id, name=args.name, main=args.main
        )
    except domain_errors.PlayerNameIsAlreadyInUse as error:
        raise PyballClientConflict(
            object="player",
            item="name",
            value=args.name,
        ) from error
    except domain_errors.PlayerSaveError as error:
        raise PyballClientError(message=f"Unknown error: {error}") from error

    return PlayerModelComplete(
        id=new_player_id,
        name=args.name,
        main=args.main,
    )


@router.put("", status_code=204)
@log_func
def update_player(args: PlayerModelComplete) -> None:
    try:
        UpdatePlayer(PlayerJsonRepository()).execute(id=args.id, name=args.name, main=args.main)
    except domain_errors.PlayerNotFound as error:
        raise PyballClientNotFound(
            object="player",
            item="id",
            value=args.id,
        )
    except domain_errors.PlayerUpdateError as error:
        # TODO: Should this be raised in the application layer?
        raise PyballClientError(message=f"Unknown error: {error}")


@router.delete("", status_code=204)
@log_func
def delete_player(args: PlayerModelOnlyId) -> None:
    try:
        DeletePlayer(PlayerJsonRepository()).execute(id=args.id)
    except domain_errors.PlayerNotFound as error:
        raise PyballClientNotFound(
            object="player",
            item="id",
            value=args.id,
        )
    except domain_errors.PlayerDeleteError as error:
        # TODO: Should this be raised in the application layer?
        raise PyballClientError(message=f"Unknown error: {error}")
