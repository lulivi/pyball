import datetime
import logging
import uuid

from typing import Dict, List, Optional, Tuple, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
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
from pyball.utils.api_exceptions import (
    PyballClientConflict,
    PyballClientError,
    PyballClientNotFound,
    PyballClientUnprocessableContent,
    PyballRedirectionNotModified,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetups")


class MeetupModelOnlyId(BaseModel):
    id: uuid.UUID


class MeetupModelBaseInfoNoId(BaseModel):
    date_time: datetime.datetime
    location: str
    possible_team_sizes: Tuple[int, ...]


class MeetupModelBaseInfo(MeetupModelOnlyId, MeetupModelBaseInfoNoId):
    """"""


class MeetupModelComplete(MeetupModelOnlyId, MeetupModelBaseInfoNoId):
    players: Optional[List[uuid.UUID]] = None
    teams: Optional[List[Team]] = None


@router.get("", response_model=Union[MeetupModelComplete, List[MeetupModelComplete]])
@log_func
def get_meetup(
    id: Optional[uuid.UUID] = None, date_time: Optional[datetime.datetime] = None
) -> Union[MeetupModelComplete, List[MeetupModelComplete]]:
    meetup_getter = GetMeetup()

    if id is None and date_time is None:
        return [
            MeetupModelComplete(
                id=meetup.id,
                date_time=meetup.date_time,
                location=meetup.location,
                possible_team_sizes=meetup.possible_team_sizes,
                players=meetup.players,
                teams=meetup.teams,
            )
            for meetup in meetup_getter.all()
        ]

    meetup: Optional[Meetup] = get_single_meetup(
        meetup_getter=meetup_getter, id=id, date_time=date_time
    )

    if meetup is None:
        raise PyballClientNotFound(object="meetup", **get_error_info(id=id, date_time=date_time))

    return MeetupModelComplete(
        id=meetup.id,
        date_time=meetup.date_time,
        location=meetup.location,
        possible_team_sizes=meetup.possible_team_sizes,
        players=meetup.players,
        teams=meetup.teams,
    )


def get_single_meetup(
    meetup_getter: GetMeetup, id: Optional[uuid.UUID], date_time: Optional[datetime.datetime]
) -> Optional[Meetup]:
    if id is not None:
        return meetup_getter.by_id(id=id)

    if date_time is None:
        raise PyballClientUnprocessableContent(
            message="The date and time is necessary if the ID is not provided",
            item="date_time",
        )

    return meetup_getter.by_date_time(date_time=date_time)


def get_error_info(
    id: Optional[uuid.UUID], date_time: Optional[datetime.datetime]
) -> Dict[str, Union[datetime.datetime, uuid.UUID]]:
    if id is not None:
        return {"item": "id", "value": id}

    return {"item": "date_time", "value": date_time}


@router.post("", response_model=MeetupModelBaseInfo, status_code=201)
@log_func
def create(args: MeetupModelBaseInfoNoId) -> MeetupModelBaseInfo:
    new_meetup_id = uuid.uuid4()

    try:
        CreateMeetup(MeetupJsonRepository()).create(
            new_meetup_id,
            date_time=args.date_time,
            location=args.location,
            possible_team_sizes=args.possible_team_sizes,
        )
    except domain_errors.MeetupDateTimeIsAlreadyUsed as error:
        raise PyballClientConflict(
            object="meetup",
            item="date_time",
            value=args.date_time.isoformat(),
        ) from error
    except domain_errors.MeetupSaveError as error:
        raise PyballClientError(message=f"Unknown error: {error}") from error

    return MeetupModelBaseInfo(
        id=new_meetup_id,
        date_time=args.date_time,
        location=args.location,
        possible_team_sizes=args.possible_team_sizes,
    )


class AddPlayerModel(BaseModel):
    meetup_id: uuid.UUID
    player_id: uuid.UUID


@router.put("/add/player", status_code=204)
@log_func
def add_player(args: AddPlayerModel) -> None:
    try:
        AddPlayerToMeetup(
            meetup_repository=MeetupJsonRepository(),
            player_checker=PlayerChecker(),
        ).add(
            meetup_id=args.meetup_id,
            player_id=args.player_id,
        )
    except application_errors.PlayerNotFound as error:
        raise PyballClientNotFound(
            object="player", item="player_id", value=args.player_id
        ) from error
    except application_errors.MeetupIdNotFound as error:
        raise PyballClientNotFound(
            object="meetup", item="meetup_id", value=args.meetup_id
        ) from error
    except application_errors.PlayerIsAlreadyInMeetup as error:
        raise PyballRedirectionNotModified(object="meetup")
