"""Get active meetup use case."""
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class GetActiveMeetup:
    """Use case for finding the current active meetup."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(self, require_teams: bool = False) -> Meetup:
        """Return the most recent active meetup, or raise MeetupNotFoundError.

        An active meetup has no recorded result. If require_teams is True,
        only meetups with assigned teams are eligible.
        """
        all_meetups = self.meetup_repository.find_all()
        active = [m for m in all_meetups if m.result is None]
        if require_teams:
            active = [m for m in active if m.teams is not None]
        if not active:
            raise MeetupNotFoundError("active")
        return max(active, key=lambda m: m.date)
