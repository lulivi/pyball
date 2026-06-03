"""Start match use case."""
from datetime import datetime

from pyball.domain.meetup.errors import MeetupHasNoTeamsError, MeetupNotFoundError
from pyball.domain.meetup.repository import MeetupRepository


class StartMatch:
    """Use case for generating the match tracking URL."""

    def __init__(self, meetup_repository: MeetupRepository, base_url: str, match_token: str = ""):
        """Initialize with repository, base URL, and optional match token."""
        self.meetup_repository = meetup_repository
        self.base_url = base_url
        self.match_token = match_token

    def execute(self, meetup_date: datetime) -> str:
        """Return the match tracking URL, or raise if meetup is missing or has no teams."""
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")
        if self.match_token:
            return f"{self.base_url}/match?token={self.match_token}"
        return f"{self.base_url}/match"
