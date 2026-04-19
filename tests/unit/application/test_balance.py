"""Tests for the balanced-teams scoring logic."""

from datetime import datetime

import pytest

from pyball.application.meetup.balance import (
    compute_player_scores,
    extract_winning_counts,
    optimize_teams,
)
from pyball.domain.meetup.models import MatchResult, Meetup, PlayerId, Team


def _finished_meetup(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_str: str,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
    events: tuple = (),
) -> Meetup:
    """Build a finished Meetup for testing."""
    m = Meetup.create(datetime.strptime(date_str, "%Y-%m-%d %H:%M"), "Campo")
    for pid in team_a + team_b:
        m.add_player(pid)
    m.set_teams([Team.create("A", team_a), Team.create("B", team_b)])
    m.set_result(MatchResult(score_a=score_a, score_b=score_b, events=events))
    return m


class TestComputePlayerScores:
    """Tests for compute_player_scores."""

    def test_winner_scores_higher_than_loser(self):
        """Player who always wins gets a higher score than player who always loses."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetups = [_finished_meetup(f"2025-10-0{i} 20:00", [p1], [p2], 2, 0) for i in range(1, 4)]
        scores = compute_player_scores([p1, p2], meetups, meetups)
        assert scores[p1] > scores[p2]

    def test_falls_back_to_all_time_when_below_season_threshold(self):
        """Player with < 3 season matches uses full-history data instead."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        # 2 season matches — p1 wins both (below threshold)
        season = [
            _finished_meetup("2025-10-01 20:00", [p1], [p2], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1], [p2], 2, 0),
        ]
        # 3 old matches — p2 wins all (makes p2 stronger in full history)
        old = [
            _finished_meetup("2024-10-01 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-08 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-15 20:00", [p2], [p1], 2, 0),
        ]
        all_meetups = season + old
        scores = compute_player_scores([p1, p2], season, all_meetups)
        # Both below threshold → both use full history → p2 wins 3/5 vs p1 2/5
        assert scores[p2] > scores[p1]

    def test_no_history_player_gets_group_average(self):
        """Player with no match history receives the mean of all other players' scores."""
        p1, p2, p_new = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
        meetups = [_finished_meetup(f"2025-10-0{i} 20:00", [p1], [p2], 2, 0) for i in range(1, 4)]
        scores = compute_player_scores([p1, p2, p_new], meetups, meetups)
        expected_mean = (scores[p1] + scores[p2]) / 2
        assert abs(scores[p_new] - expected_mean) < 1e-9

    def test_all_scores_in_unit_interval(self):
        """Every returned score is in [0.0, 1.0]."""
        players = [PlayerId.generate() for _ in range(4)]
        p_a, p_b = players[:2], players[2:]
        meetups = [
            _finished_meetup("2025-10-01 20:00", p_a, p_b, 3, 1),
            _finished_meetup("2025-10-08 20:00", p_b, p_a, 2, 0),
            _finished_meetup("2025-10-15 20:00", p_a, p_b, 1, 0),
        ]
        scores = compute_player_scores(players, meetups, meetups)
        for pid, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score out of range for {pid}: {score}"

    def test_all_no_history_returns_half(self):
        """When no player has history, everyone gets 0.5."""
        players = [PlayerId.generate() for _ in range(3)]
        scores = compute_player_scores(players, [], [])
        for score in scores.values():
            assert score == pytest.approx(0.5)


class TestExtractWinningCounts:
    """Tests for extract_winning_counts."""

    def test_counts_shared_wins_for_pairs(self):
        """Players who win together accumulate a shared win count."""
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        # p1+p2 win twice, p3+p4 win once
        meetups = [
            _finished_meetup("2025-10-01 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-15 20:00", [p3, p4], [p1, p2], 2, 0),
        ]
        counts = extract_winning_counts(meetups)

        key_12 = tuple(sorted([str(p1.value), str(p2.value)]))
        key_34 = tuple(sorted([str(p3.value), str(p4.value)]))
        assert counts[key_12] == 2
        assert counts[key_34] == 1

    def test_empty_when_no_meetups(self):
        """An empty meetup list returns empty counts."""
        assert not extract_winning_counts([])

    def test_keys_are_sorted_string_pairs(self):
        """All dict keys are (str, str) tuples with the smaller UUID string first."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup = _finished_meetup("2025-10-01 20:00", [p1, p2], [], 2, 0)
        counts = extract_winning_counts([meetup])

        for key in counts:
            assert isinstance(key, tuple) and len(key) == 2
            assert key[0] <= key[1]


class TestOptimizeTeams:
    """Tests for optimize_teams."""

    def test_all_players_assigned_exactly_once(self):
        """Every input player appears in exactly one output team."""
        player_ids = [PlayerId.generate() for _ in range(6)]
        scores = {pid: 0.5 for pid in player_ids}

        team_a, team_b = optimize_teams(player_ids, scores, {})

        all_assigned = team_a + team_b
        assert len(all_assigned) == len(player_ids)
        assert set(all_assigned) == set(player_ids)

    def test_raises_with_fewer_than_two_players(self):
        """optimize_teams raises ValueError for fewer than 2 players."""
        pid = PlayerId.generate()
        with pytest.raises(ValueError, match="Need at least 2"):
            optimize_teams([pid], {pid: 0.5}, {})

    def test_teams_split_evenly(self):
        """Teams differ in size by at most 1 player."""
        player_ids = [PlayerId.generate() for _ in range(7)]
        scores = {pid: 0.5 for pid in player_ids}

        team_a, team_b = optimize_teams(player_ids, scores, {})

        assert abs(len(team_a) - len(team_b)) <= 1

    def test_produces_varied_results(self):
        """Repeated calls with identical input produce more than one distinct composition."""
        player_ids = [PlayerId.generate() for _ in range(4)]
        scores = {pid: 0.5 for pid in player_ids}

        compositions = set()
        for _ in range(30):
            team_a, _ = optimize_teams(player_ids, scores, {})
            compositions.add(frozenset(team_a))

        assert len(compositions) > 1

    def test_winning_pair_bonus_influences_balance(self):
        """A dominant winning pair is separated when it reduces the score imbalance."""
        # p1 and p2 have won together 10 times; p3 and p4 have no shared history
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        key = tuple(sorted([str(p1.value), str(p2.value)]))
        winning_counts = {key: 10}
        scores = {p1: 0.5, p2: 0.5, p3: 0.5, p4: 0.5}

        # Run many times: p1 and p2 should end up on different teams more often than not
        same_team_count = 0
        trials = 100
        for _ in range(trials):
            team_a, team_b = optimize_teams([p1, p2, p3, p4], scores, winning_counts)
            if p1 in team_a and p2 in team_a:
                same_team_count += 1
            if p1 in team_b and p2 in team_b:
                same_team_count += 1

        # Separated more than 50% of the time (pair bonus discourages co-location)
        assert same_team_count < trials * 0.5
