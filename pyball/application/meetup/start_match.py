"""Start match use case."""

import urllib.parse
from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.exceptions import MeetupError


class MeetupHasNoTeamsError(MeetupError):
    """Raised when trying to start a match without teams."""


class StartMatch:
    """Use case for generating a match tracking URL."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
        base_url: str,
    ):
        """Initialize with repositories and the base URL."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository
        self.base_url = base_url

    def execute(self, date_str: str) -> str:
        """Generate the match tracking URL for the given meetup date.

        Args:
            date_str: Meetup date in 'YYYY/MM/DD HH:MM' format.

        Returns:
            URL string with encoded team names and date.

        Raises:
            MeetupNotFoundError: If no meetup exists on that date.
            MeetupHasNoTeamsError: If the meetup has no teams yet.
        """
        try:
            meetup_date = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
        except ValueError as exc:
            raise ValueError("Invalid date format. Use: YYYY/MM/DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")

        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        team_a_names = [player_names[str(pid.value)] for pid in meetup.teams[0].players]
        team_b_names = [player_names[str(pid.value)] for pid in meetup.teams[1].players]

        params = urllib.parse.urlencode(
            {
                "date": meetup_date.strftime("%Y-%m-%dT%H:%M"),
                "teamA": ",".join(team_a_names),
                "teamB": ",".join(team_b_names),
            }
        )
        return f"{self.base_url}/?{params}"
