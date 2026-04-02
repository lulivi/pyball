"""Create meetup use case."""

from datetime import datetime

from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class CreateMeetup:
    """Use case for creating a new meetup."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, date: datetime) -> Meetup:
        existing = self.meetup_repository.find_by_date(date.date())
        if existing:
            existing.date = date
            self.meetup_repository.save(existing)
            return existing
        meetup = Meetup.create(date)
        self.meetup_repository.save(meetup)
        return meetup