"""Create teams use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.exceptions import MeetupError


class CreateTeams:
    """Use case for creating random teams."""

    def __init__(self, meetup_repository: MeetupRepository):
        """Initialize with a meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, date_str: str) -> Meetup:
        """Create random teams for a meetup by date string."""
        try:
            meetup_date = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
        except ValueError as exc:
            raise InvalidMeetupDateError("Invalid date format. Use: YYYY/MM/DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if not meetup:
            raise MeetupNotFoundError(date_str)

        meetup.create_random_teams()
        self.meetup_repository.save(meetup)
        return meetup


class InvalidMeetupDateError(ValueError, MeetupError):
    """Raised when meetup date format is invalid."""
