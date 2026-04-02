"""Create teams use case."""

import random

from pyball.domain.meetup.models import MeetupId
from pyball.domain.meetup.repository import MeetupRepository


class CreateTeams:
    """Use case for creating balanced teams."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, meetup_id: str) -> Meetup:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            from pyball.domain.meetup.errors import MeetupNotFoundError
            raise MeetupNotFoundError(meetup_id)

        meetup.create_balanced_teams(random)
        self.meetup_repository.save(meetup)
        return meetup