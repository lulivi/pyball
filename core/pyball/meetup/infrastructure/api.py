import datetime
import logging
import uuid

from typing import List, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pyball.logger import log_func
from pyball.meetup.application import errors as application_errors
from pyball.meetup.application.add_player_to_meetup import AddPlayerToMeetup
from pyball.meetup.application.create_meetup import CreateMeetup
from pyball.meetup.domain import errors as domain_errors
from pyball.meetup.domain.model.meetup import Meetup, Team
from pyball.meetup.infrastructure.get_meetup import GetMeetup
from pyball.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository
from pyball.meetup.infrastructure.player_checker import PlayerChecker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetups")


class MeetupGetIn(BaseModel):
    id: Optional[uuid.UUID] = None
    date_time: Optional[datetime.datetime] = None


class MeetupGetOut(BaseModel):
    id: uuid.UUID
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...] = (5, 6)
    players: Optional[List[uuid.UUID]] = None
    teams: Optional[List[Team]] = None


@router.get("", response_model=Union[MeetupGetOut, List[MeetupGetOut]])
@log_func
def get_meetup(
    id: Optional[uuid.UUID] = None, date_time: Optional[datetime.datetime] = None
) -> Union[MeetupGetOut, List[MeetupGetOut]]:

    if id is None and date_time is None:
        return [
            MeetupGetOut(
                id=meetup.id,
                date_time=meetup.date_time,
                location=meetup.location,
                possible_team_sizes=meetup.possible_team_sizes,
                players=meetup.players,
                teams=meetup.teams,
            )
            for meetup in GetMeetup().all()
        ]

    meetup: Optional[Meetup] = get_single_meetup(id=id, date_time=date_time)

    if meetup is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"The meetup `{id or date_time}` was not found",
                }
            },
        )

    return MeetupGetOut(
        id=meetup.id,
        date_time=meetup.date_time,
        location=meetup.location,
        possible_team_sizes=meetup.possible_team_sizes,
        players=meetup.players,
        teams=meetup.teams,
    )


def get_single_meetup(
    id: Optional[uuid.UUID], date_time: Optional[datetime.datetime]
) -> Optional[Meetup]:
    meetup_getter = GetMeetup()

    if id is not None:
        return meetup_getter.by_id(id=id)

    if date_time is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {"message": "The date and time is necessary if the ID is not provided"}
            },
        )

    return meetup_getter.by_date_time(date_time=date_time)


class CreateMeetupIn(BaseModel):
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...]


class MeetupCreateOut(CreateMeetupIn):
    id: uuid.UUID


@router.post("", response_model=MeetupCreateOut)
@log_func
def create(args: CreateMeetupIn) -> MeetupCreateOut:
    new_meetup_id = uuid.uuid4()
    meetup_repository = MeetupJsonRepository()

    try:
        CreateMeetup(meetup_repository=meetup_repository).create(
            new_meetup_id,
            date_time=args.date_time,
            location=args.location,
            possible_team_sizes=args.possible_team_sizes,
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

    return MeetupCreateOut(
        id=new_meetup_id,
        date_time=args.date_time,
        location=args.location,
        possible_team_sizes=args.possible_team_sizes,
    )


class AddPlayerIn(BaseModel):
    meetup_id: uuid.UUID
    player_id: uuid.UUID


@router.put("/add/player", status_code=204)
@log_func
def add_player(args: AddPlayerIn):
    try:
        AddPlayerToMeetup(
            meetup_repository=MeetupJsonRepository(),
            player_checker=PlayerChecker(),
        ).add(
            meetup_id=args.meetup_id,
            player_id=args.player_id,
        )
    except application_errors.PlayerNotFound as error:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Player not found `{error.id}`",
                    "value": "player_id",
                }
            },
        )
    except application_errors.MeetupIdNotFound as error:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Meetup not found `{error.id}`",
                    "value": "meetup_id",
                }
            },
        )
    except application_errors.PlayerIsAlreadyInMeetup as error:
        raise HTTPException(status_code=304)
