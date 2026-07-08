"""Tests for the triangular round-robin next-round calculator."""

import random

import pytest

from pyball.domain.meetup.models import Match, MatchResult, Team
from pyball.domain.meetup.next_round_calculator import calculate_next_round, pick_first_pairing
from pyball.domain.player.models import PlayerId

TEAM_A = Team.create("A", [PlayerId.generate()])
TEAM_B = Team.create("B", [PlayerId.generate()])
TEAM_C = Team.create("C", [PlayerId.generate()])
TEAMS = (TEAM_A, TEAM_B, TEAM_C)


def _result(a: int, b: int) -> MatchResult:
    return MatchResult(score_a=a, score_b=b, events=())


class TestPickFirstPairing:
    """Tests for pick_first_pairing."""

    def test_returns_two_of_three_teams(self):
        """pick_first_pairing returns 2 distinct teams from the given 3."""
        playing = pick_first_pairing(TEAMS, rng=random.Random(0))
        assert len(playing) == 2
        assert set(playing).issubset(set(TEAMS))
        assert playing[0] != playing[1]

    def test_is_random_across_seeds(self):
        """pick_first_pairing varies its outcome across different rng seeds."""
        outcomes = {pick_first_pairing(TEAMS, rng=random.Random(seed)) for seed in range(20)}
        assert len(outcomes) > 1


class TestCalculateNextRoundFirstMatch:
    """Tests for calculate_next_round when matches is empty."""

    def test_empty_history_delegates_to_pick_first_pairing(self):
        """With no match history, calculate_next_round delegates to pick_first_pairing."""
        playing = calculate_next_round(TEAMS, [], rng=random.Random(0))
        assert len(playing) == 2
        assert set(playing).issubset(set(TEAMS))


class TestCalculateNextRoundWin:
    """Tests for the win branch of the ruleset."""

    def test_winner_stays_loser_leaves(self):
        """After a decisive win, the winner stays on and the resting team enters."""
        matches = [Match(teams_playing=(TEAM_A, TEAM_B), result=_result(2, 0))]
        stays, entering = calculate_next_round(TEAMS, matches)
        assert stays == TEAM_A
        assert entering == TEAM_C

    def test_winner_forced_out_after_three_in_a_row(self):
        """A team that wins 3 matches in a row is forced to sit out the next one."""
        matches = [
            Match(teams_playing=(TEAM_A, TEAM_B), result=_result(2, 0)),
            Match(teams_playing=(TEAM_A, TEAM_C), result=_result(2, 0)),
            Match(teams_playing=(TEAM_A, TEAM_B), result=_result(2, 0)),
        ]
        stays, entering = calculate_next_round(TEAMS, matches)
        # A just hit its 3rd straight win and must sit out; the loser (B) stays
        # on, and C — who was waiting during this last match — enters. A must
        # NOT reappear immediately, or the max-streak rule would be pointless.
        assert stays == TEAM_B
        assert entering == TEAM_C

    def test_winner_with_only_two_in_a_row_keeps_playing(self):
        """A team that has only won 2 in a row is not yet forced out."""
        matches = [
            Match(teams_playing=(TEAM_A, TEAM_B), result=_result(2, 0)),
            Match(teams_playing=(TEAM_A, TEAM_C), result=_result(2, 0)),
        ]
        stays, entering = calculate_next_round(TEAMS, matches)
        assert stays == TEAM_A
        assert entering == TEAM_B


class TestCalculateNextRoundDraw:
    """Tests for the draw branch of the ruleset."""

    def test_team_with_more_consecutive_played_sits_out(self):
        """On a draw, the team with the longer consecutive-play streak sits out."""
        matches = [
            Match(teams_playing=(TEAM_A, TEAM_B), result=_result(1, 0)),
            Match(teams_playing=(TEAM_A, TEAM_C), result=_result(1, 1)),
        ]
        # TEAM_A has played 2 in a row, TEAM_C just rotated in (1) -> A sits out.
        # B — who was waiting during this last match — enters; A must NOT
        # reappear immediately, or the tie-break rule would be pointless.
        stays, entering = calculate_next_round(TEAMS, matches)
        assert stays == TEAM_C
        assert entering == TEAM_B

    def test_first_match_draw_is_random_tie_break(self):
        """A draw with equal streaks is broken randomly across rng seeds."""
        matches = [Match(teams_playing=(TEAM_A, TEAM_B), result=_result(1, 1))]
        outcomes = {
            calculate_next_round(TEAMS, matches, rng=random.Random(seed))[0] for seed in range(20)
        }
        assert outcomes == {TEAM_A, TEAM_B}

    def test_calculate_next_round_raises_if_last_match_unresolved(self):
        """calculate_next_round raises ValueError if the last match has no result."""
        matches = [Match(teams_playing=(TEAM_A, TEAM_B))]
        with pytest.raises(ValueError, match="no result"):
            calculate_next_round(TEAMS, matches)
