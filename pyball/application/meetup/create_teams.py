# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Create balanced teams use case."""

import logging
from datetime import date, datetime

from pyball.application.meetup.create_teams_algorithms.algorithm import TeamAssignmentAlgorithm
from pyball.domain.meetup.errors import MeetupLockedError, MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.meetup.next_round_calculator import ensure_first_match
from pyball.domain.meetup.repository import MeetupRepository

logger = logging.getLogger(__name__)


class CreateTeams:
    """Use case for creating history-aware balanced teams."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        algorithm: TeamAssignmentAlgorithm,
    ) -> None:
        """Initialize with a meetup repository and an assignment algorithm."""
        self.meetup_repository = meetup_repository
        self.algorithm = algorithm

    def execute(self, meetup_date: datetime, team_count: int = 2) -> Meetup:
        """Create teams for a meetup by delegating to the injected algorithm."""
        if team_count not in (2, 3):
            raise ValueError("team_count must be 2 or 3")

        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if not meetup:
            raise MeetupNotFoundError(str(meetup_date))
        if meetup.locked:
            raise MeetupLockedError(f"Meetup at {meetup_date} is locked, cannot regenerate teams.")

        if len(meetup.players) < team_count:
            raise ValueError(f"Need at least {team_count} players to create teams.")

        all_meetups = self.meetup_repository.find_all()
        finished = [m for m in all_meetups if m.matches and m.matches[-1].result is not None]
        season_start = _season_start(date.today())
        season_start_dt = datetime.combine(season_start, datetime.min.time())
        season_meetups = [m for m in finished if m.date.date() >= season_start]

        assignments = self.algorithm.assign(
            meetup.players, finished, season_meetups, season_start_dt, team_count
        )

        names = ["A", "B", "C"][:team_count]
        meetup.set_teams(
            [
                Team.create(name, assignment.players, goalkeeper=assignment.goalkeeper)
                for name, assignment in zip(names, assignments)
            ]
        )
        ensure_first_match(meetup)
        self.meetup_repository.save(meetup)
        logger.info(
            "Teams generated for %s: %d teams from %d players (%s)",
            meetup_date,
            team_count,
            len(meetup.players),
            type(self.algorithm).__name__,
        )
        return meetup


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)
