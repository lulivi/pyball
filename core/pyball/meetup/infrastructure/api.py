import datetime
import uuid

from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pyball.meetup.application import errors as application_errors
from pyball.meetup.application.add_player_to_meetup import AddPlayerToMeetup
from pyball.meetup.application.create_meetup import CreateMeetup
from pyball.meetup.application.get_meetup import GetMeetup
from pyball.meetup.domain import errors as domain_errors
from pyball.meetup.domain.model.meetup import Meetup, Team
from pyball.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository
from pyball.meetup.infrastructure.player_checker import PlayerChecker
from pyball.player.domain.model.player import Player
from pyball.player.infrastructure.get_player import GetPlayer

router = APIRouter(prefix="/meetup")


class MeetupOut(BaseModel):
    id: uuid.UUID
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...] = (5, 6)
    players: Optional[List[uuid.UUID]] = None
    teams: Optional[List[Team]] = None


@router.get("/all", response_model=List[MeetupOut])
def get_all_meetups() -> MeetupOut:
    return [
        MeetupOut(
            id=meetup.id,
            date_time=meetup.date_time,
            location=meetup.location,
            possible_team_sizes=meetup.possible_team_sizes,
            players=meetup.players,
            teams=meetup.teams,
        )
        for meetup in GetMeetup(MeetupJsonRepository()).all()
    ]


@router.get("/{meetup_id}", response_model=MeetupOut)
def get_meetup(meetup_id: uuid.UUID) -> MeetupOut:
    try:
        meetup: Meetup = GetMeetup(MeetupJsonRepository()).by_id(id=meetup_id)
    except application_errors.MeetupIdNotFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"The meetup ID {meetup_id} was not found",
                    "value": "meetup_id",
                }
            },
        )

    return MeetupOut(
        id=meetup.id,
        date_time=meetup.date_time,
        location=meetup.location,
        possible_team_sizes=meetup.possible_team_sizes,
        players=meetup.players,
        teams=meetup.teams,
    )


class CreateMeetupIn(BaseModel):
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...]


class CreateMeetupOut(CreateMeetupIn):
    id: uuid.UUID


@router.post("/create", response_model=CreateMeetupOut)
def create(create_arguments: CreateMeetupIn) -> CreateMeetupOut:
    new_meetup_id = uuid.uuid4()
    meetup_repository = MeetupJsonRepository()

    try:
        CreateMeetup(meetup_repository=meetup_repository).create(
            new_meetup_id,
            date_time=create_arguments.date_time,
            location=create_arguments.location,
            possible_team_sizes=create_arguments.possible_team_sizes,
        )
    except domain_errors.MeetupDateTimeIsAlreadyUsed as error:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "message": f"Datetime already in use {error.date_time}",
                    "type": "duplication",
                    "value": "date_time,",
                }
            },
        )
    except domain_errors.MeetupSaveError as error:
        raise HTTPException(
            status_code=499,
            detail={"error": {"message": f"Unknown error: {error}", "type": "unknown"}},
        )

    return CreateMeetupOut(
        id=new_meetup_id,
        date_time=create_arguments.date_time,
        location=create_arguments.location,
        possible_team_sizes=create_arguments.possible_team_sizes,
    )


class AddPlayerIn(BaseModel):
    player_id: uuid.UUID


@router.put("/{meetup_id}/add_player", status_code=204)
def add_player(meetup_id: uuid.UUID, args: AddPlayerIn):
    try:
        AddPlayerToMeetup(
            meetup_repository=MeetupJsonRepository(),
            player_checker=PlayerChecker(),
        ).add(
            meetup_id=meetup_id,
            player_id=args.player_id,
        )
    except application_errors.PlayerNotFound as error:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Player not found {args.player_id}",
                    "value": "player_id",
                }
            },
        )
    except application_errors.MeetupIdNotFound as error:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Meetup not found {meetup_id}",
                    "value": "meetup_id",
                }
            },
        )
    except application_errors.PlayerIsAlreadyInMeetup as error:
        raise HTTPException(status_code=304)
