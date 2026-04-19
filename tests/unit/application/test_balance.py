"""Tests for the balanced-teams scoring logic."""

from datetime import datetime

import pytest

from pyball.application.meetup.balance import compute_player_scores
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
