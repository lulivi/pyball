import uuid

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pyball.player.application.create_player import CreatePlayer
from pyball.player.domain import errors as domain_errors
from pyball.player.domain.model.player import Player
from pyball.player.infrastructure.get_player import GetPlayer
from pyball.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository

router = APIRouter(prefix="/player")


class PlayerOut(BaseModel):
    id: uuid.UUID
    name: str
    main: bool = False


@router.get("/all", response_model=List[PlayerOut])
def get_all_players() -> PlayerOut:
    return [
        PlayerOut(
            id=player.id,
            name=player.name,
            main=player.main,
        )
        for player in GetPlayer().all()
    ]


@router.get("/{player_id}", response_model=PlayerOut)
def get_player(player_id: uuid.UUID) -> PlayerOut:
    try:
        player: Player = GetPlayer().by_id(id=player_id)
    except domain_errors.PlayerNotFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"The player ID `{player_id}` was not found",
                    "value": "player_id",
                }
            },
        )

    return PlayerOut(
        id=player.id,
        name=player.name,
        main=player.main,
    )


@router.get("/by_name/{player_name}", response_model=PlayerOut)
def get_player(player_name: str) -> PlayerOut:
    player: Optional[Player] = GetPlayer().by_name(name=player_name)

    if player is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"The player name `{player_name}` was not found",
                    "value": "player_name",
                }
            },
        )

    return PlayerOut(
        id=player.id,
        name=player.name,
        main=player.main,
    )


class CreatePlayerIn(BaseModel):
    name: str
    main: bool = False


class CreatePlayerOut(CreatePlayerIn):
    id: uuid.UUID


@router.post("/create", response_model=CreatePlayerOut)
def create_player(args: CreatePlayerIn) -> CreatePlayerOut:
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

    return CreatePlayerOut(
        id=new_player_id,
        name=args.name,
        main=args.main,
    )
