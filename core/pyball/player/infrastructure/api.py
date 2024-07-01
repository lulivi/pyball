import logging
import uuid

from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pyball.logger import log_func
from pyball.player.application.create_player import CreatePlayer
from pyball.player.domain import errors as domain_errors
from pyball.player.domain.model.player import Player
from pyball.player.infrastructure.get_player import GetPlayer
from pyball.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/players")


class PlayerGetIn(BaseModel):
    id: Optional[uuid.UUID] = None
    name: Optional[str] = None


class PlayerGetOut(BaseModel):
    id: uuid.UUID
    name: str
    main: bool = False


@router.get("", response_model=Union[PlayerGetOut, List[PlayerGetOut]])
@log_func
def get_player(
    id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
) -> Union[PlayerGetOut, List[PlayerGetOut]]:
    if id is None and name is None:
        return [
            PlayerGetOut(
                id=player.id,
                name=player.name,
                main=player.main,
            )
            for player in GetPlayer().all()
        ]

    player: Optional[Player] = get_single_player(id=id, name=name)

    if player is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"The player `{id or name}` was not found",
                }
            },
        )

    return PlayerGetOut(
        id=player.id,
        name=player.name,
        main=player.main,
    )


def get_single_player(
    id: Optional[uuid.UUID] = None, name: Optional[str] = None
) -> Optional[Player]:
    player_getter = GetPlayer()

    if id is not None:
        return player_getter.by_id(id=id)

    if name is None:
        raise HTTPException(
            status_code=422,
            detail={"error": {"message": "Name is necessary if the ID is not provided"}},
        )

    return player_getter.by_name(name=name)


class PlayerCreateIn(BaseModel):
    name: str
    main: bool = False


class PlayerCreateOut(PlayerCreateIn):
    id: uuid.UUID


@router.post("", response_model=PlayerCreateOut)
@log_func
def create_player(args: PlayerCreateIn) -> PlayerCreateOut:
    new_player_id = uuid.uuid4()

    try:
        CreatePlayer(PlayerSqlitoRepository()).create(
            id=new_player_id, name=args.name, main=args.main
        )
    except domain_errors.PlayerNameIsAlreadyInUse as error:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "message": f"The player name `{args.name}` is already in use",
                    "value": "name",
                }
            },
        )
    except domain_errors.PlayerSaveError as error:
        raise HTTPException(
            status_code=499,
            detail={"error": {"message": f"Unknown error: {error}"}},
        )

    return PlayerCreateOut(
        id=new_player_id,
        name=args.name,
        main=args.main,
    )
