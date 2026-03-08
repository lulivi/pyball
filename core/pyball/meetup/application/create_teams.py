import datetime
import uuid

from typing import Optional

from pyball.meetup.application.errors import InvalidPlayerCount, MeetupIdNotFound
from pyball.meetup.domain.meetups import Meetups
from pyball.meetup.domain.model.meetup import Meetup


class CreateTeams:
    def __init__(self, meetup_repository: Meetups) -> None:
        self._meetups = meetup_repository

    def execute(
        self,
        id: uuid.UUID,
    ) -> None:
        meetup: Optional[Meetup] = self._meetups.get(id=id)

        if meetup is None:
            raise MeetupIdNotFound(id=id)

        if not meetup.player_count_is_valid():
            raise InvalidPlayerCount()

        meetup.create_teams()
        self._meetups.save(meetup=meetup)
