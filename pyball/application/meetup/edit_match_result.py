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
"""Edit match result use case."""

from datetime import datetime

from pyball.application.meetup.finish_match import _build_goal_events
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import MatchResult
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


class EditMatchResult:
    """Use case for replacing the result of a finished match."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ):
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(
        self,
        date_str: str,
        events: list[dict],
        final_score: dict[str, int],
        match_index: int = -1,
    ):
        """Replace the result of a specific match for the given meetup.

        Unlike FinishMatch, does not raise MeetupAlreadyClosedError — it overwrites a
        result regardless of whether the meetup is already closed, and does not
        recompute or append any further rounds.

        Args:
            date_str: Meetup date in ISO format (e.g. '2026-05-28T20:00').
            events: List of goal event dicts with keys:
                    scorer (str), assistant (str|None), team (str), timestamp (str HH:MM).
            final_score: Dict with keys 'A' and 'B' mapping to int scores.
            match_index: Which match in meetup.matches to overwrite. Defaults to -1
                (the most recent match), which is always correct for classic meetups
                (exactly one match) and for editing the latest round of a triangular.

        Returns:
            The updated Meetup.

        Raises:
            MeetupNotFoundError: If no meetup on that date.
            ValueError: If date is invalid, meetup has no teams or matches, or a
                        player name cannot be fuzzy-matched.
        """
        try:
            meetup_date = datetime.fromisoformat(date_str)
        except ValueError as exc:
            raise ValueError("Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM") from exc

        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.teams is None:
            raise ValueError("Cannot set result without teams")
        if not meetup.matches:
            raise ValueError("Cannot set result without a match")

        all_players = self.player_repository.find_all()
        goal_events = _build_goal_events(events, all_players)
        result = MatchResult(
            score_a=final_score["A"],
            score_b=final_score["B"],
            events=tuple(goal_events),
        )
        meetup.matches[match_index].result = result
        self.meetup_repository.save(meetup)
        return meetup
