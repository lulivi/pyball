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

"""Tests for match-outcome and winning-pair-count pure domain helpers."""

from datetime import datetime

from pyball.domain.meetup.match_stats import pair_key, winning_pair_counts
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team


def _finished_meetup(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_str: str,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
) -> Meetup:
    """Build a finished Meetup for testing."""
    meetup = Meetup.create(datetime.strptime(date_str, "%Y-%m-%d %H:%M"), "Campo")
    for pid in team_a + team_b:
        meetup.add_player(pid)
    team_a_obj, team_b_obj = Team.create("A", team_a), Team.create("B", team_b)
    meetup.set_teams([team_a_obj, team_b_obj])
    meetup.add_match(
        Match(
            teams_playing=(team_a_obj, team_b_obj),
            result=MatchResult(score_a=score_a, score_b=score_b, events=()),
        )
    )
    return meetup


class TestPairKey:
    """Tests for pair_key."""

    def test_returns_smaller_id_first(self):
        """pair_key sorts the two string IDs so the smaller one is first."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        key = pair_key(p1, p2)
        assert key == pair_key(p2, p1)
        assert key[0] <= key[1]


class TestWinningPairCounts:
    """Tests for winning_pair_counts."""

    def test_counts_shared_wins_for_pairs(self):
        """Players who win together accumulate a shared win count."""
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        meetups = [
            _finished_meetup("2025-10-01 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-15 20:00", [p3, p4], [p1, p2], 2, 0),
        ]
        counts = winning_pair_counts(meetups)
        key_12 = pair_key(p1, p2)
        key_34 = pair_key(p3, p4)
        assert counts[key_12] == 2
        assert counts[key_34] == 1

    def test_empty_when_no_meetups(self):
        """An empty meetup list returns empty counts."""
        assert not winning_pair_counts([])

    def test_draw_produces_no_counts(self):
        """A drawn match contributes no winning pairs."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup = _finished_meetup("2025-10-01 20:00", [p1, p2], [], 1, 1)
        assert not winning_pair_counts([meetup])
