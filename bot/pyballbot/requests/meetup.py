import datetime
import functools
import locale
import uuid

from typing import Dict, List, Optional, Tuple, Union, cast

from pyballbot.logger import log_func
from pyballbot.requests import player as player_requests
from pyballbot.requests.errors import (
    AddPlayerToMeetupError,
    CreateMatchesError,
    CreateTeamsError,
    InvalidPlayerCount,
    MeetupCreationError,
    MeetupDateTimeDoesNotExist,
    MeetupDateTimeIsAlreadyInUse,
    MeetupIdDoesNotExist,
    MeetupQueryError,
    PlayerIdDoesNotExist,
    PlayerIsAreadyCalled,
    PlayerIsNotCalled,
    RemovePlayerFromMeetupError,
)
from pyballbot.requests.types import DisplayMeetup, Meetup, Player, Response
from pyballbot.requests.utils import BaseEndpoint, RequestMethod, get_response


@log_func
def get_display_meetup(id: uuid.UUID) -> DisplayMeetup:
    meetup: Meetup = get_by(id=id)
    id_to_player_translator = {}
    display_meetup_players = []
    display_meetup_teams = []

    for player_id in meetup.players:
        player = player_requests.get_by(id=player_id)
        id_to_player_translator[player_id] = player
        display_meetup_players.append(player)

    display_meetup_players.sort(
        key=functools.cmp_to_key(
            lambda player_1, player_2: locale.strcoll(player_1.name, player_2.name)
        )
    )

    for team in meetup.teams:
        display_team = []
        for player_id in team:
            display_team.append(id_to_player_translator[player_id])
        display_meetup_teams.append(
            sorted(
                display_team,
                key=functools.cmp_to_key(
                    lambda player_1, player_2: locale.strcoll(player_1.name, player_2.name)
                ),
            )
        )

    return DisplayMeetup(
        date_time=meetup.date_time,
        location=meetup.location,
        players=sorted(
            display_meetup_players,
            key=functools.cmp_to_key(
                lambda player_1, player_2: locale.strcoll(player_1.name, player_2.name)
            ),
        ),
        teams=display_meetup_teams,
    )


@log_func
def get_all() -> List[Meetup]:
    return cast(List[Meetup], _get())


@log_func
def get_by(**kwargs) -> Meetup:
    if len(kwargs) != 1:
        raise MeetupQueryError(
            "None or more than one element where specified in the single query call"
        )

    return cast(Meetup, _get(**kwargs))


@log_func
def _get(
    id: Optional[uuid.UUID] = None, date_time: Optional[datetime.datetime] = None
) -> Union[Player, List[Player]]:
    response: Response = get_response(
        request_method=RequestMethod.GET,
        base_endpoint=BaseEndpoint.MEETUPS,
        params=_get_params(id=id, date_time=date_time),
    )

    if response.status != 200:
        if response.status == 404:
            if id is not None:
                raise MeetupIdDoesNotExist(id=id)
            raise MeetupDateTimeDoesNotExist(date_time=date_time)
        raise MeetupQueryError(str(response.json))

    if isinstance(response.json, list):
        return [Meetup.from_json(json_meetup) for json_meetup in response.json]

    return Meetup.from_json(response.json)


def _get_params(
    id: Optional[uuid.UUID], date_time: Optional[datetime.datetime] = None
) -> Optional[Dict[str, str]]:
    if id is not None:
        return {"id": str(id)}

    if date_time is not None:
        return {"date_time": date_time.isoformat()}

    return None


@log_func
def translate_date_to_id(date_time: datetime.datetime) -> uuid.UUID:
    response: Response = get_response(
        request_method=RequestMethod.GET,
        base_endpoint=BaseEndpoint.MEETUPS,
        route="/translate_date",
        params={"date_time": date_time.isoformat()},
    )

    if response.status != 200:
        if response.status == 404:
            raise MeetupDateTimeDoesNotExist(date_time=date_time)
        raise MeetupQueryError(str(response.json))

    return uuid.UUID(response.json["id"])


@log_func
def create(
    date_time: datetime.datetime,
    location: str,
    possible_team_sizes: Tuple[int, ...],
) -> None:
    response: Response = get_response(
        request_method=RequestMethod.POST,
        base_endpoint=BaseEndpoint.MEETUPS,
        route="",
        json={
            "date_time": date_time.isoformat(),
            "location": location,
            "possible_team_sizes": possible_team_sizes,
        },
    )

    if response.status != 201:
        if response.status == 409:
            raise MeetupDateTimeIsAlreadyInUse(date_time=date_time)
        raise MeetupCreationError(str(response.json))


def add_player_by_name(
    meetup_id: uuid.UUID,
    player_name: str,
):
    player: Player = player_requests.get_by(name=player_name)
    add_player(meetup_id=meetup_id, player_id=player.id)


def add_player(meetup_id: uuid.UUID, player_id: uuid.UUID):
    response: Response = get_response(
        request_method=RequestMethod.PUT,
        base_endpoint=BaseEndpoint.MEETUPS,
        route="/add/player",
        json={"meetup_id": str(meetup_id), "player_id": str(player_id)},
    )

    if response.status != 204:
        if response.status == 404:
            if response.json["error"]["item"] == "player_id":
                raise PlayerIdDoesNotExist(id=player_id)
            raise MeetupIdDoesNotExist(id=meetup_id)

        if response.status == 304:
            raise PlayerIsAreadyCalled(meetup_id=meetup_id, player_id=player_id)

        raise AddPlayerToMeetupError(str(response.json))


def remove_player_by_name(
    meetup_id: uuid.UUID,
    player_name: str,
):
    player: Player = player_requests.get_by(name=player_name)
    remove_player(meetup_id=meetup_id, player_id=player.id)


def remove_player(meetup_id: uuid.UUID, player_id: uuid.UUID):
    response: Response = get_response(
        request_method=RequestMethod.PUT,
        base_endpoint=BaseEndpoint.MEETUPS,
        route="/remove/player",
        json={"meetup_id": str(meetup_id), "player_id": str(player_id)},
    )

    if response.status != 204:
        if response.status == 404:
            if response.json["error"]["item"] == "player_id":
                raise PlayerIdDoesNotExist(id=player_id)
            raise MeetupIdDoesNotExist(id=meetup_id)

        if response.status == 304:
            raise PlayerIsNotCalled(meetup_id=meetup_id, player_id=player_id)

        raise RemovePlayerFromMeetupError(str(response.json))


def create_teams(meetup_id: uuid.UUID) -> None:
    response: Response = get_response(
        request_method=RequestMethod.PUT,
        base_endpoint=BaseEndpoint.MEETUPS,
        route="/create_teams",
        json={"id": str(meetup_id)},
    )

    if response.status != 201:
        if response.status == 404:
            raise MeetupIdDoesNotExist(id=meetup_id)

        if response.status == 409:
            raise InvalidPlayerCount()

        raise CreateTeamsError(str(response.json))


def create_matches(meetup_id: uuid.UUID) -> None:
    # Not implemented
    return
    response: Response = get_response(
        request_method=RequestMethod.POST,
        base_endpoint=BaseEndpoint.MATCHES,
        route="",
        json={"meetup_id": str(meetup_id)},
    )

    if response.status != 204:
        # Check
        if response.status == 404:
            raise MeetupIdDoesNotExist(id=meetup_id)

        if response.status == 409:
            raise InvalidPlayerCount()

        raise CreateMatchesError(str(response.json))
