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

"""Tests for RandomAlgorithm."""

from datetime import datetime

from pyball.application.meetup.create_teams_algorithms.random import RandomAlgorithm
from pyball.domain.meetup.models import PlayerId


class TestRandomAlgorithm:
    """Tests for RandomAlgorithm."""

    def test_all_players_assigned_exactly_once(self):
        """Every input player appears in exactly one output team."""
        players = [PlayerId.generate() for _ in range(6)]
        algo = RandomAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        team_a, team_b = assignments[0].players, assignments[1].players
        assert set(team_a + team_b) == set(players)
        assert len(team_a) + len(team_b) == len(players)

    def test_teams_split_evenly(self):
        """Teams differ by at most 1 player."""
        players = [PlayerId.generate() for _ in range(7)]
        algo = RandomAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        team_a, team_b = assignments[0].players, assignments[1].players
        assert abs(len(team_a) - len(team_b)) <= 1

    def test_works_with_empty_history(self):
        """RandomAlgorithm does not raise when given empty meetup lists."""
        players = [PlayerId.generate() for _ in range(4)]
        algo = RandomAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        assert sum(len(a.players) for a in assignments) == 4

    def test_no_player_duplicated_across_teams(self):
        """No player appears in both teams."""
        players = [PlayerId.generate() for _ in range(8)]
        algo = RandomAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        team_a, team_b = assignments[0].players, assignments[1].players
        assert not set(team_a) & set(team_b)

    def test_random_algorithm_never_sets_a_goalkeeper(self):
        """RandomAlgorithm always returns goalkeeper=None, regardless of position."""
        players = [PlayerId.generate() for _ in range(4)]
        algo = RandomAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        assert all(a.goalkeeper is None for a in assignments)
