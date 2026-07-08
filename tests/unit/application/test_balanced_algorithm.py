"""Tests for BalancedAlgorithm and its internal scoring helpers."""

from datetime import datetime, time

import pytest

from pyball.application.meetup.create_teams_algorithms.balanced import (
    BalancedAlgorithm,
    _player_role,
    _team_score,
    compute_player_scores,
    extract_winning_counts,
    optimize_teams,
)
from pyball.domain.meetup.errors import UnknownAlgorithmError
from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, PlayerId, Team


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
    team_a_obj, team_b_obj = Team.create("A", team_a), Team.create("B", team_b)
    m.set_teams([team_a_obj, team_b_obj])
    m.add_match(
        Match(
            teams_playing=(team_a_obj, team_b_obj),
            result=MatchResult(score_a=score_a, score_b=score_b, events=events),
        )
    )
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
        season = [
            _finished_meetup("2025-10-01 20:00", [p1], [p2], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1], [p2], 2, 0),
        ]
        old = [
            _finished_meetup("2024-10-01 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-08 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-15 20:00", [p2], [p1], 2, 0),
        ]
        all_meetups = season + old
        scores = compute_player_scores([p1, p2], season, all_meetups)
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
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        key = tuple(sorted([str(p1.value), str(p2.value)]))
        winning_counts = {key: 10}
        scores = {p1: 0.5, p2: 0.5, p3: 0.5, p4: 0.5}

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


class TestTeamScore:
    """Tests for _team_score."""

    def test_returns_sum_of_player_scores_with_no_pair_wins(self):
        """Without pair-win history, score equals the sum of individual scores."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        scores = {p1: 0.6, p2: 0.4}
        result = _team_score([p1, p2], scores, {}, max_pair_wins=0)
        assert result == pytest.approx(1.0)


class TestPlayerRole:
    """Tests for _player_role."""

    def test_scorer_when_more_goals_than_assists(self):
        """Player with more goals than assists is classified as 'scorer'."""
        p = PlayerId.generate()
        scorer_id = p
        meetups = [
            _finished_meetup(
                f"2025-10-0{i} 20:00",
                [p],
                [],
                2,
                0,
                events=(
                    GoalEvent(
                        scorer_id=scorer_id, assistant_id=None, team="A", timestamp=time(20, i)
                    ),
                    GoalEvent(
                        scorer_id=scorer_id, assistant_id=None, team="A", timestamp=time(20, i + 1)
                    ),
                ),
            )
            for i in range(1, 4)
        ]
        role = _player_role(p, meetups)
        assert role == "scorer"

    def test_neutral_when_no_history(self):
        """Player with no history gets 'neutral' role."""
        p = PlayerId.generate()
        role = _player_role(p, [])
        assert role == "neutral"

    def test_assister_when_assists_greater_than_goals(self):
        """Player with more assists than goals is classified as assister."""
        p1 = PlayerId.generate()
        meetups = []
        for i in range(3):
            team_a, team_b = Team.create("A", [p1]), Team.create("B", [PlayerId.generate()])
            m = Meetup.create(datetime(2025, 10, i + 1, 20, 0), "Campo")
            m.add_player(p1)
            m.set_teams([team_a, team_b])
            events = [
                GoalEvent(
                    scorer_id=PlayerId.generate(),
                    assistant_id=p1,
                    team="B",
                    timestamp=time(20, 10),
                )
                for _ in range(2)
            ]
            events.append(
                GoalEvent(
                    scorer_id=p1,
                    assistant_id=PlayerId.generate(),
                    team="A",
                    timestamp=time(20, 15),
                )
            )
            m.add_match(
                Match(
                    teams_playing=(team_a, team_b),
                    result=MatchResult(score_a=3, score_b=0, events=tuple(events)),
                )
            )
            meetups.append(m)

        role = _player_role(p1, meetups)
        assert role == "assister"

    def test_falls_back_to_season_then_history(self):
        """Uses season first (<3 matches), then full history if available."""
        p1 = PlayerId.generate()
        season = []
        for i in range(2):
            team_a, team_b = Team.create("A", [p1]), Team.create("B", [PlayerId.generate()])
            m = Meetup.create(datetime(2025, 10, i + 1, 20, 0), "Campo")
            m.add_player(p1)
            m.set_teams([team_a, team_b])
            events = (
                GoalEvent(
                    scorer_id=p1,
                    assistant_id=PlayerId.generate(),
                    team="A",
                    timestamp=time(20, 10),
                ),
            )
            m.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, events)))
            season.append(m)
        history = []
        for i in range(3):
            team_a, team_b = Team.create("A", [p1]), Team.create("B", [PlayerId.generate()])
            m = Meetup.create(datetime(2024, 10, i + 1, 20, 0), "Campo")
            m.add_player(p1)
            m.set_teams([team_a, team_b])
            events = (
                GoalEvent(
                    scorer_id=PlayerId.generate(),
                    assistant_id=p1,
                    team="B",
                    timestamp=time(20, 10),
                ),
            )
            m.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, events)))
            history.append(m)

        role = _player_role(p1, season, history)
        assert role == "assister"


class TestBalancedAlgorithmAssign:
    """Tests for BalancedAlgorithm.assign()."""

    def test_all_players_assigned_to_exactly_two_teams(self):
        """assign() returns two groups covering all input players with no duplicates."""
        players = [PlayerId.generate() for _ in range(6)]
        algo = BalancedAlgorithm()
        team_a, team_b = algo.assign(players, [], [], datetime(2025, 9, 1))
        assert set(team_a + team_b) == set(players)
        assert len(team_a) + len(team_b) == len(players)

    def test_teams_differ_by_at_most_one_player(self):
        """Teams produced by assign() are roughly even in size."""
        players = [PlayerId.generate() for _ in range(7)]
        algo = BalancedAlgorithm()
        team_a, team_b = algo.assign(players, [], [], datetime(2025, 9, 1))
        assert abs(len(team_a) - len(team_b)) <= 1


class TestUnknownAlgorithmError:
    """Tests for UnknownAlgorithmError."""

    def test_message_includes_name_and_available(self):
        """Error message lists the unknown name and the available algorithms."""
        err = UnknownAlgorithmError("xyz", ["balanceado", "random"])
        assert "xyz" in str(err)
        assert "balanceado" in str(err)
        assert "random" in str(err)

    def test_attributes_accessible(self):
        """name and available attributes are set correctly."""
        err = UnknownAlgorithmError("foo", ["balanceado"])
        assert err.name == "foo"
        assert err.available == ["balanceado"]
