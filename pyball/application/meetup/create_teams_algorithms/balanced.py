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
"""History-aware balanced team assignment algorithm.

This module builds two teams from the players registered in a meetup by
combining three ideas:

1. Estimate each player's current strength from historical performance.
2. Score complete team partitions, not just individual swaps.
3. Choose from a broad pool of good candidates to preserve variety.

The flow is intentionally split into small helpers so each stage is easy to
reason about:

- ``compute_player_scores()`` calculates a normalized strength score in
  ``[0, 1]`` for every player. It prefers current-season data when there is
  enough sample size, and falls back to all-time history otherwise. The score
  is a weighted combination of goals per match, assists per match, and win
  rate.
- ``compute_player_roles()`` classifies each player as ``scorer``,
  ``assister``, or ``neutral``. This is a lightweight extra signal used only
  to avoid highly lopsided compositions.
- ``extract_winning_counts()`` measures how often pairs of players have won
  together in the past. Those counts are later used as a diversity penalty so
  the algorithm does not keep recreating the same successful pairings.

Once those inputs are prepared, ``optimize_teams()`` evaluates complete
partitions:

- For typical meetup sizes, it enumerates every unique split of players into
  two teams. When the player count grows beyond the exhaustive threshold, it
  switches to sampled random partitions instead.
- Each partition is scored with ``_assignment_cost()``. The cost has three
  components: strength imbalance between both teams, repeated winning-pair
  penalty, and role imbalance penalty.
- Candidates are sorted by total cost, and ``_selection_pool()`` keeps a broad
  pool of near-best options rather than only the single optimum. This is the
  key design choice that improves variety between runs.
- ``_weighted_choice()`` performs the final pick. Lower-cost teams are still
  more likely, but several strong alternatives remain viable, so repeated
  executions do not collapse into the same composition unless the data really
  leaves very few good options.

In short, this algorithm is not trying to find one mathematically perfect team
split and reuse it forever. It tries to stay balanced while also giving room
for different, still-reasonable team compositions across repeated executions.
"""

from __future__ import annotations

import itertools
import random
from datetime import datetime

from pyball.domain.meetup.models import Meetup, PlayerId
from pyball.infrastructure.persistence.legacy_stats import LegacyStats

_SEASON_MIN_MATCHES = 3
_ROLE_WEIGHT = 0.15
_W_GOALS = 0.40
_W_ASSISTS = 0.30
_W_WINS = 0.30
_PAIR_WEIGHT = 1.0
_MAX_EXHAUSTIVE_PLAYERS = 18
_SAMPLED_CANDIDATES = 3000
_MIN_SELECTION_POOL = 8
_MAX_SELECTION_POOL = 24
_SELECTION_POOL_FRACTION = 0.15
_COST_EPSILON = 0.20
_WEIGHTED_PICK_TEMPERATURE = 0.08


class BalancedAlgorithm:
    """History-aware team assignment using score optimization and role balancing."""

    def __init__(self, legacy_stats: LegacyStats | None = None) -> None:
        """Initialize with optional legacy stats for pre-app historical data."""
        self.legacy_stats = legacy_stats

    def assign(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        players: list[PlayerId],
        finished_meetups: list[Meetup],
        season_meetups: list[Meetup],
        season_start: datetime,
        team_count: int = 2,
    ) -> tuple[list[PlayerId], ...]:
        """Assign players to team_count balanced groups using historical performance data."""
        if team_count not in (2, 3):
            raise ValueError("team_count must be 2 or 3")
        player_scores = compute_player_scores(
            players, season_meetups, finished_meetups, self.legacy_stats, season_start
        )
        if team_count == 2:
            player_roles = compute_player_roles(
                players, season_meetups, finished_meetups, self.legacy_stats, season_start
            )
            winning_counts = extract_winning_counts(finished_meetups)
            team_a, team_b = optimize_teams(players, player_scores, winning_counts, player_roles)
            return (team_a, team_b)
        return _snake_draft(players, player_scores, team_count)


def optimize_teams(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
    role_scores: dict[PlayerId, str] | None = None,
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Assign players to two balanced teams using a broad good-candidate pool.

    For normal meetup sizes, every unique partition is scored. The final assignment
    is picked from a weighted pool of good options, so repeated calls preserve
    balance while avoiding the same few local optima every time.
    """
    if len(player_ids) < 2:
        raise ValueError("Need at least 2 players to create teams")

    if role_scores is None:
        role_scores = {}

    max_pair_wins = max(winning_counts.values(), default=0)
    if len(player_ids) <= _MAX_EXHAUSTIVE_PLAYERS:
        partitions = _unique_partitions(player_ids)
    else:
        partitions = _sampled_partitions(player_ids)

    cost_config: AssignmentCostConfig = (
        player_scores,
        winning_counts,
        max_pair_wins,
        role_scores,
    )
    candidates = [
        (
            _assignment_cost(team_a, team_b, cost_config),
            team_a,
            team_b,
        )
        for team_a, team_b in partitions
    ]
    return _weighted_choice(_selection_pool(candidates))


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
    """Return sorted (pid_a, pid_b) -> shared win count for all player pairs."""
    counts: dict[tuple[str, str], int] = {}
    for meetup in meetups:
        for match in meetup.matches:
            if match.result is None:
                continue
            score_a, score_b = match.result.score_a, match.result.score_b
            for i, team in enumerate(match.teams_playing):
                team_wins = (score_a > score_b) if i == 0 else (score_b > score_a)
                if team_wins:
                    for pid_a, pid_b in itertools.combinations(team.players, 2):
                        key_list = [str(pid_a.value), str(pid_b.value)]
                        key: tuple[str, str] = tuple(sorted(key_list))  # type: ignore[assignment]
                        counts[key] = counts.get(key, 0) + 1
    return counts


def _selection_pool(
    candidates: list[tuple[float, list[PlayerId], list[PlayerId]]],
) -> list[tuple[float, list[PlayerId], list[PlayerId]]]:
    """Return a broad pool of good candidates to preserve variety."""
    candidates.sort(key=lambda candidate: candidate[0])
    best_cost = candidates[0][0]
    target_size = min(
        _MAX_SELECTION_POOL,
        max(_MIN_SELECTION_POOL, int(len(candidates) * _SELECTION_POOL_FRACTION)),
    )
    pool = [candidate for candidate in candidates if candidate[0] <= best_cost + _COST_EPSILON]
    if len(pool) < _MIN_SELECTION_POOL:
        pool = candidates[:_MIN_SELECTION_POOL]
    return pool[:target_size]


def _weighted_choice(
    candidates: list[tuple[float, list[PlayerId], list[PlayerId]]],
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Pick a candidate, favoring lower cost without collapsing to the single best."""
    best_cost = candidates[0][0]
    weights = [
        1.0 / (1.0 + ((cost - best_cost) / _WEIGHTED_PICK_TEMPERATURE))
        for cost, _, _ in candidates
    ]
    _, team_a, team_b = random.choices(candidates, weights=weights, k=1)[0]
    return list(team_a), list(team_b)


def _sampled_partitions(player_ids: list[PlayerId]) -> list[tuple[list[PlayerId], list[PlayerId]]]:
    """Return random unique-ish partitions for player counts too large to exhaustively search."""
    partitions: list[tuple[list[PlayerId], list[PlayerId]]] = []
    seen: set[frozenset[PlayerId]] = set()
    team_a_size = len(player_ids) // 2

    while len(partitions) < _SAMPLED_CANDIDATES:
        players = list(player_ids)
        random.shuffle(players)
        team_a = players[:team_a_size]
        team_b = players[team_a_size:]
        key = frozenset(team_a)
        mirror_key = frozenset(team_b)
        if key in seen or mirror_key in seen:
            continue
        seen.add(key)
        partitions.append((team_a, team_b))

    return partitions


def _unique_partitions(player_ids: list[PlayerId]) -> list[tuple[list[PlayerId], list[PlayerId]]]:
    """Return unique two-team partitions, avoiding mirrored duplicates."""
    team_a_size = len(player_ids) // 2
    if team_a_size == 0:
        return []

    partitions: list[tuple[list[PlayerId], list[PlayerId]]] = []

    def _append_partition(team_a: list[PlayerId]) -> None:
        team_a_set = set(team_a)
        team_b = [pid for pid in player_ids if pid not in team_a_set]
        partitions.append((team_a, team_b))

    if len(player_ids) % 2 == 0:
        anchor = player_ids[0]
        for rest in itertools.combinations(player_ids[1:], team_a_size - 1):
            _append_partition([anchor, *rest])
    else:
        for combination in itertools.combinations(player_ids, team_a_size):
            _append_partition(list(combination))

    return partitions


AssignmentCostConfig = tuple[
    dict[PlayerId, float], dict[tuple[str, str], int], int, dict[PlayerId, str]
]


def _assignment_cost(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    config: AssignmentCostConfig,
) -> float:
    """Return total assignment cost: strength balance plus composition diversity."""
    player_scores, winning_counts, max_pair_wins, role_scores = config
    balance_cost = abs(
        _team_strength(team_a, player_scores) - _team_strength(team_b, player_scores)
    )
    pair_cost = _pair_repeat_penalty(team_a, team_b, winning_counts, max_pair_wins)
    role_cost = _role_imbalance_penalty(team_a, team_b, role_scores) if role_scores else 0.0
    return balance_cost + (_PAIR_WEIGHT * pair_cost) + (_ROLE_WEIGHT * role_cost)


def _role_imbalance_penalty(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    role_scores: dict[PlayerId, str],
) -> float:
    """Return a normalized scorer-ratio imbalance penalty."""

    def _scorer_ratio(team: list[PlayerId]) -> float:
        if not team:
            return 0.0
        return sum(1 for pid in team if role_scores.get(pid) == "scorer") / len(team)

    return abs(_scorer_ratio(team_a) - _scorer_ratio(team_b))


def _pair_repeat_penalty(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    winning_counts: dict[tuple[str, str], int],
    max_pair_wins: int,
) -> float:
    """Return a normalized penalty for keeping historically successful pairs together."""
    if max_pair_wins == 0:
        return 0.0

    repeated_strength = 0.0
    total_pairs = 0
    for team in (team_a, team_b):
        for pid_a, pid_b in itertools.combinations(team, 2):
            key: tuple[str, str] = tuple(  # type: ignore[assignment]
                sorted([str(pid_a.value), str(pid_b.value)])
            )
            repeated_strength += winning_counts.get(key, 0) / max_pair_wins
            total_pairs += 1

    if total_pairs == 0:
        return 0.0
    return repeated_strength / total_pairs


def _team_strength(team: list[PlayerId], player_scores: dict[PlayerId, float]) -> float:
    """Return the team's raw player strength without composition penalties."""
    return sum(player_scores.get(pid, 0.5) for pid in team)


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
        total -= (pair_wins / max_pair_wins) * _PAIR_WEIGHT
    return total + role_penalty


def _normalize(values: list[float]) -> list[float]:
    """Normalize a list of floats to [0, 1]. Returns [0.5, ...] if all equal."""
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


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
            for match in meetup.matches:
                if match.result is None:
                    continue
                for event in match.result.events:
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
        assists += legacy_stats.get_assists(pid_str, from_date)

    if goals > assists:
        return "scorer"
    if assists > goals:
        return "assister"
    return "neutral"


def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> tuple[int, float, float, float]:
    """Return (matches_played, goals_per_match, assists_per_match, win_rate)."""
    goals = assists = wins = mp = 0
    for meetup in meetups:
        for match in meetup.matches:
            if match.result is None:
                continue
            score_a, score_b = match.result.score_a, match.result.score_b
            for i, team in enumerate(match.teams_playing):
                if player_id in team.players:
                    mp += 1
                    team_wins = (score_a > score_b) if i == 0 else (score_b > score_a)
                    if team_wins:
                        wins += 1
            for event in match.result.events:
                if event.scorer_id == player_id:
                    goals += 1
                if event.assistant_id == player_id:
                    assists += 1
    if legacy_stats and mp > 0:
        pid_str = str(player_id.value)
        assists += legacy_stats.get_assists(pid_str, from_date)

    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp


def _snake_draft(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    team_count: int,
) -> tuple[list[PlayerId], ...]:
    """Distribute players into team_count groups via a score-sorted snake draft.

    Players are sorted strongest-first and dealt out in a 0,1,2,2,1,0,0,1,2,...
    zig-zag order, which keeps summed team strength close without the
    combinatorial partition search `optimize_teams` uses for 2 teams. The list is
    shuffled before the (stable) sort so that players tied on score — the common
    case when there's little or no match history — land in a different team each
    time instead of always repeating the same grouping.
    """
    shuffled = list(player_ids)
    random.shuffle(shuffled)
    ordered = sorted(shuffled, key=lambda pid: player_scores.get(pid, 0.5), reverse=True)
    teams: list[list[PlayerId]] = [[] for _ in range(team_count)]
    index = 0
    forward = True
    for pid in ordered:
        teams[index].append(pid)
        if forward:
            index += 1
            if index == team_count:
                index = team_count - 1
                forward = False
        else:
            index -= 1
            if index < 0:
                index = 0
                forward = True
    return tuple(teams)
