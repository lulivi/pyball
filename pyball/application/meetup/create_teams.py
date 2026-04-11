"""Create teams use case."""

import random

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class CreateTeams:
    """Use case for creating balanced teams."""

    def __init__(self, meetup_repository: MeetupRepository):
        """Initialize with a meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, date_str: str) -> Meetup:
        """Create balanced teams for a meetup by date string."""
        try:
            meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            raise InvalidMeetupDateError("Invalid date format. Use: YYYY-MM-DD HH:MM")

        all_meetups = self.meetup_repository.find_all()
        meetup = None
        for m in all_meetups:
            if m.date == meetup_date:
                meetup = m
                break

        if not meetup:
            raise MeetupNotFoundError(date_str)

        meetup.create_balanced_teams(random)
        self.meetup_repository.save(meetup)
        return meetup


class InvalidMeetupDateError(ValueError):
    """Raised when meetup date format is invalid."""

    pass
