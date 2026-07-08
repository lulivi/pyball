"""Tests for team assignment algorithms with team_count generalization."""

from datetime import datetime

from pyball.application.meetup.create_teams_algorithms.balanced import (
    BalancedAlgorithm,
    extract_winning_counts,
)
from pyball.application.meetup.create_teams_algorithms.random import RandomAlgorithm
from pyball.domain.meetup.models import Match, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId


class TestRandomAlgorithmTeamCount:
    """RandomAlgorithm.assign with team_count."""

    def test_default_team_count_is_two(self):
        """Omitting team_count defaults to a two-group split."""
        players = [PlayerId.generate() for _ in range(6)]
        groups = RandomAlgorithm().assign(players, [], [], None)
        assert len(groups) == 2

    def test_three_groups_partitions_all_players(self):
        """team_count=3 returns three groups covering every input player exactly once."""
        players = [PlayerId.generate() for _ in range(9)]
        groups = RandomAlgorithm().assign(players, [], [], None, team_count=3)
        assert len(groups) == 3
        all_assigned = [pid for group in groups for pid in group]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_are_roughly_even(self):
        """Nine players split into team_count=3 produce three equal-sized groups."""
        players = [PlayerId.generate() for _ in range(9)]
        groups = RandomAlgorithm().assign(players, [], [], None, team_count=3)
        assert sorted(len(g) for g in groups) == [3, 3, 3]


class TestBalancedAlgorithmTeamCount:
    """BalancedAlgorithm.assign with team_count."""

    def test_default_team_count_is_two_and_unchanged(self):
        """Omitting team_count defaults to the existing two-team optimization path."""
        players = [PlayerId.generate() for _ in range(6)]
        groups = BalancedAlgorithm().assign(players, [], [], None)
        assert len(groups) == 2
        all_assigned = [pid for group in groups for pid in group]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_partitions_all_players(self):
        """team_count=3 returns three groups covering every input player exactly once."""
        players = [PlayerId.generate() for _ in range(9)]
        groups = BalancedAlgorithm().assign(players, [], [], None, team_count=3)
        assert len(groups) == 3
        all_assigned = [pid for group in groups for pid in group]
        assert sorted(str(p.value) for p in all_assigned) == sorted(str(p.value) for p in players)

    def test_three_groups_are_roughly_even(self):
        """Nine players split into team_count=3 produce groups differing by at most one."""
        players = [PlayerId.generate() for _ in range(9)]
        groups = BalancedAlgorithm().assign(players, [], [], None, team_count=3)
        sizes = sorted(len(g) for g in groups)
        assert sizes[-1] - sizes[0] <= 1


class TestExtractWinningCountsReadsMatches:
    """extract_winning_counts must read Meetup.matches, not the removed Meetup.result."""

    def test_extract_winning_counts_reads_matches_not_result(self):
        """extract_winning_counts must read meetup.matches, not the removed meetup.result."""
        meetup = Meetup.create(datetime(2024, 1, 1, 20, 0), "Campo")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        team_a, team_b = Team.create("A", [p1, p2]), Team.create("B", [])
        meetup.teams = [team_a, team_b]
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(3, 0, ())))

        counts = extract_winning_counts([meetup])

        key = tuple(sorted([str(p1.value), str(p2.value)]))
        assert counts[key] == 1
