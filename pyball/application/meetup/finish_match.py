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
"""Finish match use case."""

from datetime import datetime, time

from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import GoalEvent, MatchResult
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.exceptions import MeetupError


class MeetupAlreadyClosedError(MeetupError):
    """Raised when trying to finish a match that already has a result."""


class FinishMatch:
    """Use case for recording the match result."""

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
    ):
        """Save the match result for the given meetup.

        Args:
            date_str: Meetup date in ISO format (e.g. '2026-04-15T20:00').
            events: List of goal event dicts with keys:
                    scorer (str), assistant (str|None), team (str), timestamp (str ISO).
            final_score: Dict with keys 'A' and 'B' mapping to int scores.

        Returns:
            The updated Meetup.

        Raises:
            MeetupNotFoundError: If no meetup on that date.
            MeetupAlreadyClosedError: If the meetup already has a result.
            ValueError: If a player name cannot be fuzzy-matched.
        """
        try:
            meetup_date = datetime.fromisoformat(date_str)
        except ValueError as exc:
            raise ValueError("Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.is_closed():
            raise MeetupAlreadyClosedError(f"Match on {date_str} is already closed.")

        all_players = self.player_repository.find_all()

        goal_events = []
        for e in events:
            scorer_match = fuzzy_match_player(e["scorer"], all_players)
            assistant_id = None
            if e.get("assistant"):
                assistant_match = fuzzy_match_player(e["assistant"], all_players)
                assistant_id = assistant_match.player_id
            goal_events.append(
                GoalEvent(
                    scorer_id=scorer_match.player_id,
                    assistant_id=assistant_id,
                    team=e["team"],
                    timestamp=time.fromisoformat(e["timestamp"]),
                )
            )

        result = MatchResult(
            score_a=final_score["A"],
            score_b=final_score["B"],
            events=tuple(goal_events),
        )
        meetup.set_result(result)
        self.meetup_repository.save(meetup)
        return meetup
