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

"""Tests for team assignment algorithms with team_count generalization."""

from pyball.application.meetup.create_teams_algorithms.balanced import BalancedAlgorithm
from pyball.application.meetup.create_teams_algorithms.random import RandomAlgorithm
from pyball.domain.player.models import PlayerId


class TestRandomAlgorithmTeamCount:
    """RandomAlgorithm.assign with team_count."""

    def test_default_team_count_is_two(self):
        """Omitting team_count defaults to a two-group split."""
        players = [PlayerId.generate() for _ in range(6)]
        assignments = RandomAlgorithm().assign(players, [], [], None)
        assert len(assignments) == 2

    def test_three_groups_partitions_all_players(self):
        """team_count=3 returns three groups covering every input player exactly once."""
        players = [PlayerId.generate() for _ in range(9)]
        assignments = RandomAlgorithm().assign(players, [], [], None, team_count=3)
        assert len(assignments) == 3
        all_assigned = [pid for a in assignments for pid in a.players]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_are_roughly_even(self):
        """Nine players split into team_count=3 produce three equal-sized groups."""
        players = [PlayerId.generate() for _ in range(9)]
        assignments = RandomAlgorithm().assign(players, [], [], None, team_count=3)
        assert sorted(len(a.players) for a in assignments) == [3, 3, 3]


class TestBalancedAlgorithmTeamCount:
    """BalancedAlgorithm.assign with team_count."""

    def test_default_team_count_is_two_and_unchanged(self):
        """Omitting team_count defaults to the existing two-team optimization path."""
        players = [PlayerId.generate() for _ in range(6)]
        assignments = BalancedAlgorithm().assign(players, [], [], None)
        assert len(assignments) == 2
        all_assigned = [pid for a in assignments for pid in a.players]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_partitions_all_players(self):
        """team_count=3 returns three groups covering every input player exactly once."""
        players = [PlayerId.generate() for _ in range(9)]
        assignments = BalancedAlgorithm().assign(players, [], [], None, team_count=3)
        assert len(assignments) == 3
        all_assigned = [pid for a in assignments for pid in a.players]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_are_roughly_even(self):
        """Nine players split into team_count=3 produce groups differing by at most one."""
        players = [PlayerId.generate() for _ in range(9)]
        assignments = BalancedAlgorithm().assign(players, [], [], None, team_count=3)
        sizes = sorted(len(a.players) for a in assignments)
        assert sizes[-1] - sizes[0] <= 1
