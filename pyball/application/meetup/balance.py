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
"""Balanced team creation: player scoring and team optimization."""

from __future__ import annotations

import itertools
import random
from datetime import datetime

from pyball.domain.meetup.models import Meetup, PlayerId
from pyball.infrastructure.persistence.legacy_stats import LegacyStats

_SEASON_MIN_MATCHES = 3
_ROLE_WEIGHT = 0.15
_ROLE_HARD_THRESHOLD = 0.2
_W_GOALS = 0.40
_W_ASSISTS = 0.30
_W_WINS = 0.30
_PAIR_WEIGHT = 1.0
_ITERATIONS = 500


def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> tuple[int, float, float, float]:
    """Return (matches_played, goals_per_match, assists_per_match, win_rate)."""
    goals = assists = wins = mp = 0
    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue
        score_a = meetup.result.score_a
        score_b = meetup.result.score_b
        for team in meetup.teams:
            if player_id in team.players:
                mp += 1
                team_wins = (team.name == "A" and score_a > score_b) or (
                    team.name == "B" and score_b > score_a
                )
                if team_wins:
                    wins += 1
        for event in meetup.result.events:
            if event.scorer_id == player_id:
                goals += 1
            if event.assistant_id == player_id:
                assists += 1
    if legacy_stats and mp > 0:
        pid_str = str(player_id.value)
        if from_date is not None:
            assists += legacy_stats.get_assists_since(pid_str, from_date)
        else:
            legacy = legacy_stats.get(pid_str)
            assists += legacy["assists"]

    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp


def _player_role(
    player_id: PlayerId,
    season_meetups: list[Meetup],
    all_meetups: list[Meetup] | None = None,
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> str:
    """Classify player as 'scorer', 'assister', or 'neutral' based on goals vs assists.

    Uses season data when player has >= 3 matches, otherwise falls back to
    full history. If no history exists, returns 'neutral'.
    """
    if all_meetups is None:
        all_meetups = []

    def _count_events(meetups: list[Meetup]) -> tuple[int, int]:
        goals = assists = 0
        for meetup in meetups:
            if meetup.result is None:
                continue
            for event in meetup.result.events:
                if event.scorer_id == player_id:
                    goals += 1
                if event.assistant_id == player_id:
                    assists += 1
        return goals, assists

    goals_s, assists_s = _count_events(season_meetups)
    if sum((goals_s, assists_s)) > 0 and len(season_meetups) >= _SEASON_MIN_MATCHES:
        goals, assists = goals_s, assists_s
    else:
        goals_h, assists_h = _count_events(all_meetups)
        if goals_h + assists_h > 0:
            goals, assists = goals_h, assists_h
        else:
            return "neutral"

    if legacy_stats and from_date is not None:
        pid_str = str(player_id.value)
        assists += legacy_stats.get_assists_since(pid_str, from_date)

    if goals > assists:
        return "scorer"
    if assists > goals:
        return "assister"
    return "neutral"


def _normalize(values: list[float]) -> list[float]:
    """Normalize a list of floats to [0, 1]. Returns [0.5, ...] if all equal."""
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def compute_player_scores(
    player_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> dict[PlayerId, float]:
    """Return a normalized [0, 1] strength score for each player.

    Uses season data when a player has >= _SEASON_MIN_MATCHES there, otherwise
    falls back to full history. Players with no history receive the group mean.
    """
    components: dict[PlayerId, tuple[float, float, float] | None] = {}
    for pid in player_ids:
        mp_s, gpm_s, apm_s, wr_s = _player_stats(pid, season_meetups, legacy_stats, from_date)
        if mp_s >= _SEASON_MIN_MATCHES:
            components[pid] = (gpm_s, apm_s, wr_s)
        else:
            mp_a, gpm_a, apm_a, wr_a = _player_stats(pid, all_meetups, legacy_stats, from_date)
            components[pid] = (gpm_a, apm_a, wr_a) if mp_a > 0 else None

    known = [(pid, c) for pid, c in components.items() if c is not None]
    if not known:
        return {pid: 0.5 for pid in player_ids}

    known_pids = [pid for pid, _ in known]
    norm_goals = _normalize([c[0] for _, c in known])
    norm_assists = _normalize([c[1] for _, c in known])
    norm_wins = _normalize([c[2] for _, c in known])

    known_scores = {
        pid: norm_goals[i] * _W_GOALS + norm_assists[i] * _W_ASSISTS + norm_wins[i] * _W_WINS
        for i, pid in enumerate(known_pids)
    }

    mean_score = sum(known_scores.values()) / len(known_scores)
    return {pid: known_scores.get(pid, mean_score) for pid in player_ids}


def compute_player_roles(
    player_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> dict[PlayerId, str]:
    """Return role classification ('scorer', 'assister', 'neutral') for each player.

    Uses season data when player has >= 3 matches, otherwise falls back to
    full history. Players with no history return 'neutral'.
    """
    return {
        pid: _player_role(pid, season_meetups, all_meetups, legacy_stats, from_date)
        for pid in player_ids
    }


def extract_winning_counts(meetups: list[Meetup]) -> dict[tuple[str, str], int]:
    """Return sorted (pid_a, pid_b) → shared win count for all player pairs."""
    counts: dict[tuple[str, str], int] = {}
    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue
        score_a = meetup.result.score_a
        score_b = meetup.result.score_b
        for team in meetup.teams:
            team_wins = (team.name == "A" and score_a > score_b) or (
                team.name == "B" and score_b > score_a
            )
            if team_wins:
                for pid_a, pid_b in itertools.combinations(team.players, 2):
                    key_list = [str(pid_a.value), str(pid_b.value)]
                    key: tuple[str, str] = tuple(sorted(key_list))  # type: ignore[assignment]
                    counts[key] = counts.get(key, 0) + 1
    return counts


def _team_score(
    team: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
    max_pair_wins: int,
    role_penalty: float = 0.0,
) -> float:
    """Compute the aggregate strength score for a team."""
    total = sum(player_scores.get(pid, 0.5) for pid in team)
    if max_pair_wins == 0:
        return total
    for pid_a, pid_b in itertools.combinations(team, 2):
        key: tuple[str, str] = tuple(  # type: ignore[assignment]
            sorted([str(pid_a.value), str(pid_b.value)])
        )
        pair_wins = winning_counts.get(key, 0)
        total += (pair_wins / max_pair_wins) * _PAIR_WEIGHT
    return total + role_penalty


def optimize_teams(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
    role_scores: dict[PlayerId, str] | None = None,
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Assign players to two balanced teams using local-search optimization.

    Starts from a random split and iterates _ITERATIONS times, accepting swaps
    that reduce the score difference between teams. Each call starts from a
    fresh random state, producing varied but balanced results.

    Role balancing: attempts to keep scorer/assister ratio within _ROLE_HARD_THRESHOLD.
    If not achievable, applies soft penalty after _ITERATIONS iterations.
    """
    if len(player_ids) < 2:
        raise ValueError("Need at least 2 players to create teams")

    if role_scores is None:
        role_scores = {}

    players = list(player_ids)
    random.shuffle(players)
    mid = len(players) // 2
    team_a: list[PlayerId] = players[:mid]
    team_b: list[PlayerId] = players[mid:]

    max_pair_wins = max(winning_counts.values(), default=0)

    for _ in range(_ITERATIONS):
        i = random.randrange(len(team_a))
        j = random.randrange(len(team_b))

        score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
        score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        current_diff = abs(score_a - score_b)

        team_a[i], team_b[j] = team_b[j], team_a[i]

        new_score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
        new_score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        new_diff = abs(new_score_a - new_score_b)

        if new_diff > current_diff:
            team_a[i], team_b[j] = team_b[j], team_a[i]

    if role_scores:
        config: RoleBalanceConfig = (player_scores, winning_counts, max_pair_wins, role_scores)
        team_a, team_b = _apply_role_balance(team_a, team_b, config)

    return team_a, team_b


RoleBalanceConfig = tuple[
    dict[PlayerId, float], dict[tuple[str, str], int], int, dict[PlayerId, str]
]


def _apply_role_balance(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    config: RoleBalanceConfig,
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Apply role balancing to teams after initial score optimization."""
    player_scores, winning_counts, max_pair_wins, role_scores = config

    def _count_scorers(team: list[PlayerId]) -> int:
        return sum(1 for pid in team if role_scores.get(pid) == "scorer")

    def _role_ratio(team: list[PlayerId]) -> float:
        if not team:
            return 0.0
        return _count_scorers(team) / len(team)

    def _role_penalty(team: list[PlayerId], other: list[PlayerId]) -> float:
        ratio_a = _role_ratio(team)
        ratio_b = _role_ratio(other)
        return _ROLE_WEIGHT * abs(ratio_a - ratio_b)

    for _ in range(_ITERATIONS):
        i = random.randrange(len(team_a))
        j = random.randrange(len(team_b))

        score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
        score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        current_diff = abs(score_a - score_b)

        team_a_copy = team_a.copy()
        team_b_copy = team_b.copy()
        team_a_copy[i], team_b_copy[j] = team_b[j], team_a[i]

        ratio_a = _role_ratio(team_a_copy)
        ratio_b = _role_ratio(team_b_copy)

        if abs(ratio_a - ratio_b) <= _ROLE_HARD_THRESHOLD:
            team_a[i], team_b[j] = team_b[j], team_a[i]
            new_score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
            new_score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
            new_diff = abs(new_score_a - new_score_b)

            if new_diff > current_diff:
                team_a[i], team_b[j] = team_b[j], team_a[i]

    for _ in range(200):
        i = random.randrange(len(team_a))
        j = random.randrange(len(team_b))

        score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
        score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        current_total = score_a + score_b + _role_penalty(team_a, team_b)

        team_a[i], team_b[j] = team_b[j], team_a[i]

        new_score_a = _team_score(team_a, player_scores, winning_counts, max_pair_wins)
        new_score_b = _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        new_total = new_score_a + new_score_b + _role_penalty(team_a, team_b)

        if new_total < current_total:
            team_a[i], team_b[j] = team_b[j], team_a[i]

    return team_a, team_b
