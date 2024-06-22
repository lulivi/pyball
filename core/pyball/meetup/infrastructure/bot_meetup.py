import datetime
import uuid

from pyball.greenfield.meetup.application import errors as application_errors
from pyball.greenfield.meetup.application.add_player_to_meetup import AddPlayerToMeetup
from pyball.greenfield.meetup.application.create_meetup import CreateMeetup
from pyball.greenfield.meetup.application.get_meetup import GetMeetup
from pyball.greenfield.meetup.domain import errors as domain_errors
from pyball.greenfield.meetup.infrastructure.errors import (
    MeetupDateAlreadyUsed,
    MeetupDateNotFound,
    PlayerIsAlreadyInMeetup,
    PlayerNameNotFound,
    PlayerTelegramIdNotFound,
)
from pyball.greenfield.meetup.infrastructure.get_player_by_name import GetPlayer
from pyball.greenfield.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository
from pyball.greenfield.meetup.infrastructure.player_checker import PlayerChecker
from pyball.greenfield.utils.bot import player_telegram_uuid_translator as translator


def create_meetup(
    date_time: datetime.datetime,
    location: str,
    possible_team_sizes: tuple,
) -> None:
    new_meetup_uuid = uuid.uuid4()
    meetup_repository = MeetupJsonRepository()

    try:
        CreateMeetup(meetup_repository=meetup_repository).create(
            new_meetup_uuid,
            date_time=date_time,
            location=location,
            possible_team_sizes=possible_team_sizes,
        )
    except domain_errors.MeetupDateAlreadyUsed as error:
        raise MeetupDateAlreadyUsed(date_time=error.date_time)


def add_player_to_meetup_by_telegram_id(
    meetup_date_time: datetime.datetime,
    player_telegram_id: uuid.UUID,
) -> None:
    try:
        player_id = translator.TelegramPlayerTranslatorService().translate_telegram_id(
            telegram_id=player_telegram_id
        )
    except translator.PlayerTelegramIdNotFound as error:
        raise PlayerTelegramIdNotFound(error.telegram_id)

    add_player_to_meetup(meetup_date_time=meetup_date_time, player_id=player_id)


def add_player_to_meetup_by_name(
    meetup_date_time: datetime.datetime,
    player_name: str,
) -> None:
    player = GetPlayer().by_name(player_name)
    if player is None:
        raise PlayerNameNotFound(player_name)

    add_player_to_meetup(meetup_date_time=meetup_date_time, player_id=player.id)


def add_player_to_meetup(
    meetup_date_time: datetime.datetime,
    player_id: str,
) -> None:
    meetup_repository = MeetupJsonRepository()

    try:
        meetup = GetMeetup(meetup_remository=meetup_repository).by_date(meetup_date_time)
    except application_errors.MeetupDateNotFound as error:
        raise MeetupDateNotFound(error.date_time)

    player_checker = PlayerChecker()

    try:
        AddPlayerToMeetup(meetup_repository=meetup_repository, player_checker=player_checker).add(
            meetup_id=meetup.id, player_id=player_id
        )
    except application_errors.PlayerIsAlreadyInMeetup as error:
        raise PlayerIsAlreadyInMeetup(error.meetup_id, error.player_id)
