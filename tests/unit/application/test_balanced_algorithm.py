"""Tests for BalancedAlgorithm and its internal scoring helpers."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.create_teams_algorithms.balanced import (
    BalancedAlgorithm,
    _apply_position_fit_boost,
    _position_imbalance_penalty,
    _snake_draft,
    compute_goalkeeper_scores,
    compute_player_scores,
    extract_winning_counts,
    optimize_teams,
)
from pyball.domain.meetup.errors import UnknownAlgorithmError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team
from pyball.domain.player.models import Player


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


def _finished_meetup_with_gk(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_str: str,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
    gk_a: PlayerId | None = None,
    gk_b: PlayerId | None = None,
) -> Meetup:
    """Build a finished Meetup with explicit per-team goalkeepers for testing."""
    m = Meetup.create(datetime.strptime(date_str, "%Y-%m-%d %H:%M"), "Campo")
    for pid in team_a + team_b:
        m.add_player(pid)
    team_a_obj = Team.create("A", team_a, goalkeeper=gk_a)
    team_b_obj = Team.create("B", team_b, goalkeeper=gk_b)
    m.set_teams([team_a_obj, team_b_obj])
    m.add_match(
        Match(
            teams_playing=(team_a_obj, team_b_obj),
            result=MatchResult(score_a=score_a, score_b=score_b, events=()),
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


class TestComputeGoalkeeperScores:
    """Tests for compute_goalkeeper_scores."""

    def test_fewer_conceded_scores_higher(self):
        """A goalkeeper who concedes fewer goals per match scores higher."""
        gk1, gk2 = PlayerId.generate(), PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(2)]
        meetups = [
            _finished_meetup_with_gk(
                f"2025-10-0{i} 20:00", [gk1, outfield[0]], [gk2, outfield[1]], 3, 0, gk1, gk2
            )
            for i in range(1, 4)
        ]
        scores = compute_goalkeeper_scores([gk1, gk2], meetups, meetups)
        assert scores[gk1] > scores[gk2]

    def test_no_history_candidate_gets_group_mean(self):
        """A candidate goalkeeper with no history gets the mean of known scores."""
        gk1, gk2, gk_new = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(2)]
        meetups = [
            _finished_meetup_with_gk(
                f"2025-10-0{i} 20:00", [gk1, outfield[0]], [gk2, outfield[1]], 1, 1, gk1, gk2
            )
            for i in range(1, 4)
        ]
        scores = compute_goalkeeper_scores([gk1, gk2, gk_new], meetups, meetups)
        expected_mean = (scores[gk1] + scores[gk2]) / 2
        assert abs(scores[gk_new] - expected_mean) < 1e-9

    def test_all_no_history_returns_half(self):
        """When no candidate has goalkeeper history, everyone gets 0.5."""
        candidates = [PlayerId.generate() for _ in range(3)]
        scores = compute_goalkeeper_scores(candidates, [], [])
        for score in scores.values():
            assert score == pytest.approx(0.5)

    def test_all_scores_in_unit_interval(self):
        """Every returned score is in [0.0, 1.0]."""
        gk1, gk2 = PlayerId.generate(), PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(2)]
        meetups = [
            _finished_meetup_with_gk(
                "2025-10-01 20:00", [gk1, outfield[0]], [gk2, outfield[1]], 2, 0, gk1, gk2
            ),
            _finished_meetup_with_gk(
                "2025-10-08 20:00", [gk2, outfield[1]], [gk1, outfield[0]], 1, 1, gk2, gk1
            ),
        ]
        scores = compute_goalkeeper_scores([gk1, gk2], meetups, meetups)
        for pid, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score out of range for {pid}: {score}"

    def test_ignores_matches_where_not_the_designated_goalkeeper(self):
        """Only matches where the candidate is the team's set goalkeeper count."""
        gk1 = PlayerId.generate()
        outfield = PlayerId.generate()
        # gk1 plays as an outfield player here (no team has gk1 as goalkeeper) —
        # conceded goals in this match must not count toward gk1's score.
        meetup = _finished_meetup_with_gk(
            "2025-10-01 20:00", [gk1, outfield], [PlayerId.generate()], 0, 5, None, None
        )
        scores = compute_goalkeeper_scores([gk1], [meetup], [meetup])
        assert scores[gk1] == pytest.approx(0.5)  # no goalkeeper history at all -> neutral


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


class TestOptimizeTeamsInitialSizes:
    """Tests for optimize_teams's initial_sizes handicap."""

    def test_compensates_for_a_teams_head_start(self):
        """A team that already has a member (e.g. a goalkeeper) gets a smaller split."""
        players = [PlayerId.generate() for _ in range(7)]
        scores = {pid: 0.5 for pid in players}
        team_a, team_b = optimize_teams(players, scores, {}, initial_sizes=(1, 0))
        assert len(team_a) + 1 - len(team_b) in (-1, 0, 1)


class TestPositionImbalancePenalty:
    """Tests for _position_imbalance_penalty."""

    def test_zero_when_no_positions_tagged(self):
        """No penalty when neither team has any tagged outfield position."""
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        penalty = _position_imbalance_penalty([p1, p2], [p3, p4], {})
        assert penalty == 0.0

    def test_zero_when_evenly_split(self):
        """No penalty when both teams have the same count of each position."""
        d1, d2, f1, f2 = [PlayerId.generate() for _ in range(4)]
        positions = {d1: "defensa", d2: "defensa", f1: "delantero", f2: "delantero"}
        penalty = _position_imbalance_penalty([d1, f1], [d2, f2], positions)
        assert penalty == 0.0

    def test_positive_when_lopsided(self):
        """A penalty is charged when one team hoards all of a position."""
        d1, d2, f1 = [PlayerId.generate() for _ in range(3)]
        positions = {d1: "defensa", d2: "defensa", f1: "delantero"}
        penalty = _position_imbalance_penalty([d1, d2], [f1], positions)
        assert penalty > 0.0


class TestOptimizeTeamsPositionBalance:
    """Tests for position-aware optimize_teams behavior."""

    def test_spreads_a_dominant_position_across_teams(self):
        """Four defenders and no other tagged position are split, not stacked."""
        defenders = [PlayerId.generate() for _ in range(4)]
        scores = {pid: 0.5 for pid in defenders}
        positions = {pid: "defensa" for pid in defenders}

        same_team_counts = []
        for _ in range(50):
            team_a, team_b = optimize_teams(defenders, scores, {}, positions)
            same_team_counts.append(abs(len(team_a) - len(team_b)))

        # 2-2 splits dominate; 4-0 splits are the never-happens case this guards.
        assert max(same_team_counts) <= 2


class TestBalancedAlgorithmAssign:
    """Tests for BalancedAlgorithm.assign()."""

    def test_all_players_assigned_to_exactly_two_teams(self):
        """assign() returns two groups covering all input players with no duplicates."""
        players = [PlayerId.generate() for _ in range(6)]
        algo = BalancedAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        team_a, team_b = assignments[0].players, assignments[1].players
        assert set(team_a + team_b) == set(players)
        assert len(team_a) + len(team_b) == len(players)

    def test_teams_differ_by_at_most_one_player(self):
        """Teams produced by assign() are roughly even in size."""
        players = [PlayerId.generate() for _ in range(7)]
        algo = BalancedAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        team_a, team_b = assignments[0].players, assignments[1].players
        assert abs(len(team_a) - len(team_b)) <= 1

    def test_three_teams_vary_across_repeated_calls_with_tied_scores(self):
        """Regression test: /manage's "Regenerar 3 equipos" always returned the
        same teams when players have no match history (all tied at the 0.5
        default score), because the 3-team snake draft had no randomness at all.
        """
        players = [PlayerId.generate() for _ in range(15)]
        algo = BalancedAlgorithm()
        results = {
            tuple(
                frozenset(a.players) for a in algo.assign(players, [], [], datetime(2025, 9, 1), 3)
            )
            for _ in range(20)
        }
        assert len(results) > 1

    def test_no_player_repository_means_no_goalkeeper_preassignment(self):
        """Without an injected PlayerRepository, no team ever gets a goalkeeper."""
        players = [PlayerId.generate() for _ in range(6)]
        algo = BalancedAlgorithm()
        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))
        assert all(a.goalkeeper is None for a in assignments)

    def test_goalkeepers_are_preassigned_one_per_team(self):
        """With enough portero-tagged players, every team gets a distinct goalkeeper."""
        gk1, gk2 = PlayerId.generate(), PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(4)]
        players = [gk1, gk2, *outfield]

        repo = MagicMock()
        repo.find_all.return_value = [
            Player(id=gk1, name="GK1", group="regular", position="portero"),
            Player(id=gk2, name="GK2", group="regular", position="portero"),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)

        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))

        goalkeepers = {a.goalkeeper for a in assignments}
        assert goalkeepers == {gk1, gk2}

    def test_surplus_goalkeepers_fall_back_to_the_general_pool(self):
        """A third portero with only 2 teams available still ends up on a team as a
        regular player, and every input player is still assigned exactly once."""
        gks = [PlayerId.generate() for _ in range(3)]
        outfield = [PlayerId.generate() for _ in range(3)]
        players = [*gks, *outfield]

        repo = MagicMock()
        repo.find_all.return_value = [
            *(Player(id=pid, name="GK", group="regular", position="portero") for pid in gks),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)

        assignments = algo.assign(players, [], [], datetime(2025, 9, 1))

        all_assigned = {pid for a in assignments for pid in a.players}
        assert all_assigned == set(players)
        assigned_goalkeepers = {a.goalkeeper for a in assignments if a.goalkeeper is not None}
        assert len(assigned_goalkeepers) == 2


class TestGoalkeeperPreassignmentPreservesTeamSizeBalance:
    """Regression tests: goalkeeper pre-assignment must not break team-size balance."""

    def test_triangular_sizes_differ_by_at_most_one_with_one_goalkeeper(self):
        """A 3-team triangular with one tagged keeper still splits sizes within 1."""
        gk = PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(7)]
        players = [gk, *outfield]
        repo = MagicMock()
        repo.find_all.return_value = [
            Player(id=gk, name="GK", group="regular", position="portero"),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)
        for _ in range(50):
            assignments = algo.assign(players, [], [], datetime(2025, 9, 1), 3)
            sizes = sorted(len(a.players) for a in assignments)
            assert sizes[-1] - sizes[0] <= 1

    def test_classic_sizes_differ_by_at_most_one_with_one_goalkeeper(self):
        """A classic 2-team match with one tagged keeper still splits sizes within 1."""
        gk = PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(7)]
        players = [gk, *outfield]
        repo = MagicMock()
        repo.find_all.return_value = [
            Player(id=gk, name="GK", group="regular", position="portero"),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)
        for _ in range(50):
            assignments = algo.assign(players, [], [], datetime(2025, 9, 1), 2)
            sizes = sorted(len(a.players) for a in assignments)
            assert sizes[-1] - sizes[0] <= 1

    def test_classic_three_players_one_goalkeeper_does_not_crash(self):
        """A 3-player classic match with 1 tagged keeper must not raise IndexError."""
        gk = PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(2)]
        players = [gk, *outfield]
        repo = MagicMock()
        repo.find_all.return_value = [
            Player(id=gk, name="GK", group="regular", position="portero"),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)
        for _ in range(50):
            assignments = algo.assign(players, [], [], datetime(2025, 9, 1), 2)
            sizes = sorted(len(a.players) for a in assignments)
            assert sizes[-1] - sizes[0] <= 1

    def test_goalkeeper_lands_on_different_teams_across_repeated_calls(self):
        """A single goalkeeper isn't always pre-assigned to the same team index."""
        gk = PlayerId.generate()
        outfield = [PlayerId.generate() for _ in range(5)]
        players = [gk, *outfield]
        repo = MagicMock()
        repo.find_all.return_value = [
            Player(id=gk, name="GK", group="regular", position="portero"),
            *(Player(id=pid, name="P", group="regular") for pid in outfield),
        ]
        algo = BalancedAlgorithm(player_repository=repo)
        gk_team_indices = set()
        for _ in range(50):
            assignments = algo.assign(players, [], [], datetime(2025, 9, 1), 3)
            for i, assignment in enumerate(assignments):
                if assignment.goalkeeper == gk:
                    gk_team_indices.add(i)
        assert len(gk_team_indices) > 1


class TestSnakeDraft:
    """Tests for _snake_draft (3-team balanced distribution)."""

    def test_assigns_all_players_across_three_teams(self):
        """Every player ends up in exactly one of the three teams."""
        players = [PlayerId.generate() for _ in range(15)]
        scores = {pid: 0.5 for pid in players}

        teams = _snake_draft(players, scores, 3)

        assert len(teams) == 3
        assert sum(len(team) for team in teams) == len(players)
        assert set(players) == {pid for team in teams for pid in team}

    def test_varies_across_repeated_calls_with_tied_scores(self):
        """With all-equal scores, repeated calls must not always return the
        identical grouping — this was the root cause of teams looking "stuck".
        """
        players = [PlayerId.generate() for _ in range(15)]
        scores = {pid: 0.5 for pid in players}

        results = {
            tuple(frozenset(team) for team in _snake_draft(players, scores, 3)) for _ in range(20)
        }

        assert len(results) > 1

    def test_varies_across_repeated_calls_with_distinct_scores(self):
        """This is the actual real-world bug: players with real match history
        almost never tie exactly, so a fix that only randomized tie-breaking
        (an earlier, insufficient version of this fix) left every real deployment
        with 15 players and real history still getting the identical 3 teams
        every time "Regenerar" was clicked.
        """
        players = [PlayerId.generate() for _ in range(15)]
        scores = {pid: i / 14 for i, pid in enumerate(players)}

        results = {
            tuple(frozenset(team) for team in _snake_draft(players, scores, 3)) for _ in range(20)
        }

        assert len(results) > 1

    def test_keeps_balance_with_distinct_scores(self):
        """The weighted lottery still favors balance over many draws, not just luck.

        A single draw's balance is no longer a hard guarantee now that picks are
        randomized (that's the point of this fix) — averaged over many draws it
        must still clearly beat an unweighted random 3-way split of the same
        players (empirically ~1.25 mean imbalance for this score distribution).
        """
        players = [PlayerId.generate() for _ in range(15)]
        scores = {pid: i / 14 for i, pid in enumerate(players)}

        imbalances = []
        for _ in range(300):
            teams = _snake_draft(players, scores, 3)
            totals = [sum(scores[pid] for pid in team) for team in teams]
            imbalances.append(max(totals) - min(totals))

        assert sum(imbalances) / len(imbalances) < 1.2


class TestSnakeDraftInitialSizes:
    """Tests for _snake_draft's initial_sizes handicap."""

    def test_compensates_for_a_teams_head_start(self):
        """A team that already has a member (e.g. a goalkeeper) gets fewer picks."""
        players = [PlayerId.generate() for _ in range(7)]
        scores = {pid: 0.5 for pid in players}
        teams = _snake_draft(players, scores, 3, initial_sizes=[1, 0, 0])
        sizes = [len(team) for team in teams]
        final_sizes = [sizes[0] + 1, sizes[1], sizes[2]]
        assert max(final_sizes) - min(final_sizes) <= 1


class TestApplyPositionFitBoost:
    """Tests for _apply_position_fit_boost."""

    def test_no_change_when_positions_empty(self):
        """Weights pass through unchanged when no positions are known."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        weights = [1.0, 1.0]
        boosted = _apply_position_fit_boost(weights, [p1, p2], [], {})
        assert boosted == weights

    def test_boosts_a_position_the_team_lacks(self):
        """A candidate whose position the picking team has none of gets boosted."""
        defender, forward, teammate = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
        positions = {defender: "defensa", forward: "delantero", teammate: "delantero"}
        weights = [1.0, 1.0]
        boosted = _apply_position_fit_boost(weights, [defender, forward], [teammate], positions)
        assert boosted[0] > boosted[1]  # defensa boosted, delantero (already present) not


class TestSnakeDraftPositionBalance:
    """Tests for position-aware _snake_draft behavior."""

    def test_still_assigns_every_player_with_positions_supplied(self):
        """Adding positions doesn't drop or duplicate any player."""
        players = [PlayerId.generate() for _ in range(9)]
        scores = {pid: 0.5 for pid in players}
        positions = {pid: "defensa" for pid in players[:3]}

        teams = _snake_draft(players, scores, 3, positions)

        assert sum(len(team) for team in teams) == len(players)
        assert set(players) == {pid for team in teams for pid in team}

    def test_spreads_a_tagged_position_across_teams(self):
        """Three defenders tend to land on three different teams, not stacked.

        _snake_draft's picking order isn't a fixed zig-zag: each pick goes to
        whichever team currently has the fewest total members (to keep team
        sizes balanced), with the position-fit boost then weighting *which*
        candidate that team picks. With _POSITION_FIT_BOOST=3.0, this measures
        a true stacked rate of ~32.3% (100k-trial sample: 32306/100000). At
        trials=5000, that gives a mean of ~1615.5 stacked draws with a standard
        deviation of ~33.1; the 0.37 threshold (1850) sits ~7.1 standard
        deviations above that mean, so a false failure from sampling noise
        alone is effectively impossible. It's still a tight enough threshold
        to catch a regression to no-boosting-effect: the unboosted rate is
        ~61.6% (mean ~3081 stacked draws at trials=5000), ~35.8 standard
        deviations above the 0.37 threshold.
        """
        defenders = [PlayerId.generate() for _ in range(3)]
        neutrals = [PlayerId.generate() for _ in range(6)]
        players = defenders + neutrals
        scores = {pid: 0.5 for pid in players}
        positions = {pid: "defensa" for pid in defenders}

        stacked_count = 0
        trials = 5000
        for _ in range(trials):
            teams = _snake_draft(players, scores, 3, positions)
            per_team_defenders = [sum(1 for pid in team if pid in defenders) for team in teams]
            if max(per_team_defenders) > 1:
                stacked_count += 1

        assert stacked_count < trials * 0.37


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
