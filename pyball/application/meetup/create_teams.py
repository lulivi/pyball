"""Create balanced teams use case."""

from datetime import date, datetime

from pyball.application.meetup.balance import (
    compute_player_roles,
    compute_player_scores,
    extract_winning_counts,
    optimize_teams,
)
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.exceptions import MeetupError
from pyball.infrastructure.persistence import LegacyStats


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)


class CreateTeams:
    """Use case for creating history-aware balanced teams."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        legacy_stats: LegacyStats | None = None,
    ):
        """Initialize with a meetup repository."""
        self.meetup_repository = meetup_repository
        self.legacy_stats = legacy_stats

    def execute(self, date_str: str) -> Meetup:
        """Create balanced teams for a meetup by date string."""
        try:
            meetup_date = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
        except ValueError as exc:
            raise InvalidMeetupDateError("Invalid date format. Use: YYYY/MM/DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if not meetup:
            raise MeetupNotFoundError(date_str)

        all_meetups = self.meetup_repository.find_all()
        finished = [m for m in all_meetups if m.result is not None]
        season_start = _season_start(date.today())
        season_meetups = [m for m in finished if m.date.date() >= season_start]

        season_start_dt = datetime.combine(season_start, datetime.min.time())

        player_scores = compute_player_scores(
            meetup.players, season_meetups, finished, self.legacy_stats, season_start_dt
        )
        player_roles = compute_player_roles(
            meetup.players, season_meetups, finished, self.legacy_stats, season_start_dt
        )
        winning_counts = extract_winning_counts(finished)
        team_a_ids, team_b_ids = optimize_teams(
            meetup.players, player_scores, winning_counts, player_roles
        )

        meetup.set_teams([Team.create("A", team_a_ids), Team.create("B", team_b_ids)])
        self.meetup_repository.save(meetup)
        return meetup


class InvalidMeetupDateError(ValueError, MeetupError):
    """Raised when meetup date format is invalid."""
