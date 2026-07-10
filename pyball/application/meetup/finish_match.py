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
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.domain.meetup.models import GoalEvent, Match, MatchResult
from pyball.domain.meetup.next_round_calculator import calculate_next_round
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


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
        """Save the result of the current pending match for the given meetup.

        With 2 teams, this is the meetup's only match — closes the meetup automatically.
        With 3 teams, appends the next computed round and leaves the meetup open until
        an admin explicitly closes it via CloseMeetup.

        Args:
            date_str: Meetup date in ISO format (e.g. '2026-04-15T20:00'). Accepts a
                string because this use case is invoked exclusively from the HTTP layer,
                which receives raw ISO strings from the frontend JSON body.
            events: List of goal event dicts with keys:
                    scorer (str), assistant (str|None), team (str), timestamp (str ISO).
            final_score: Dict with keys 'A' and 'B' mapping to int scores for the
                current pending match (always exactly 2 teams, regardless of meetup mode).

        Returns:
            The updated Meetup.

        Raises:
            MeetupNotFoundError: If no meetup on that date.
            MeetupAlreadyClosedError: If the meetup is already closed.
            ValueError: If there is no pending match, or a player name cannot be
                fuzzy-matched.
        """
        try:
            meetup_date = datetime.fromisoformat(date_str)
        except ValueError as exc:
            raise ValueError("Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM") from exc

        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.is_closed():
            raise MeetupAlreadyClosedError(f"Match on {date_str} is already closed.")

        all_players = self.player_repository.find_all()
        goal_events = _build_goal_events(events, all_players)
        result = MatchResult(
            score_a=final_score["A"],
            score_b=final_score["B"],
            events=tuple(goal_events),
        )
        meetup.record_result(result)

        teams = meetup.teams
        assert teams is not None  # a pending match implies teams were already assigned
        if len(teams) == 2:
            meetup.close()
        else:
            next_pairing = calculate_next_round((teams[0], teams[1], teams[2]), meetup.matches)
            meetup.add_match(Match(teams_playing=next_pairing))

        self.meetup_repository.save(meetup)
        return meetup


def _build_goal_events(events: list[dict], all_players) -> list[GoalEvent]:
    """Fuzzy-match scorer/assistant names and build GoalEvent objects."""
    goal_events = []
    for e in events:
        is_own_goal = bool(e.get("is_own_goal", False))
        if is_own_goal and e.get("assistant"):
            raise ValueError("An own goal cannot have an assistant")
        scorer_match = fuzzy_match_player(e["scorer"], all_players)
        assistant_id = None
        if not is_own_goal and e.get("assistant"):
            assistant_match = fuzzy_match_player(e["assistant"], all_players)
            assistant_id = assistant_match.player_id
        goal_events.append(
            GoalEvent(
                scorer_id=scorer_match.player_id,
                assistant_id=assistant_id,
                team=e["team"],
                timestamp=time.fromisoformat(e["timestamp"]),
                is_own_goal=is_own_goal,
            )
        )
    return goal_events
