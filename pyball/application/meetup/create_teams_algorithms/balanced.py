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
- ``_position_imbalance_penalty()`` measures how unevenly the three outfield
  positions (defensa/centrocampista/delantero) are split between two teams. This
  is a lightweight extra signal, alongside the pair-repeat penalty, that nudges
  the optimizer away from stacking one team with e.g. every tagged defender.
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
  penalty, and position imbalance penalty.
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

from pyball.application.meetup.create_teams_algorithms.algorithm import TeamAssignment
from pyball.domain.meetup.models import Meetup, PlayerId
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure.persistence.legacy_stats import LegacyStats

_SEASON_MIN_MATCHES = 3
_POSITION_WEIGHT = 0.15
_OUTFIELD_POSITIONS = ("defensa", "centrocampista", "delantero")
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
_DRAFT_PICK_TEMPERATURE = 1.5
_POSITION_FIT_BOOST = 3.0


class BalancedAlgorithm:
    """History-aware team assignment using score optimization and position balancing."""

    def __init__(
        self,
        legacy_stats: LegacyStats | None = None,
        player_repository: PlayerRepository | None = None,
    ) -> None:
        """Initialize with optional legacy stats and a player repository for positions."""
        self.legacy_stats = legacy_stats
        self.player_repository = player_repository

    def assign(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        players: list[PlayerId],
        finished_meetups: list[Meetup],
        season_meetups: list[Meetup],
        season_start: datetime,
        team_count: int = 2,
    ) -> tuple[TeamAssignment, ...]:
        """Assign players to team_count balanced groups using historical performance data."""
        if team_count not in (2, 3):
            raise ValueError("team_count must be 2 or 3")

        positions = self._player_positions(players)
        goalkeeper_candidates = [pid for pid in players if positions.get(pid) == "portero"]
        gk_scores = compute_goalkeeper_scores(
            goalkeeper_candidates, season_meetups, finished_meetups
        )
        goalkeeper_per_team, remaining_players = _assign_goalkeepers(
            players, positions, gk_scores, team_count
        )
        initial_sizes = [1 if gk is not None else 0 for gk in goalkeeper_per_team]

        player_scores = compute_player_scores(
            remaining_players, season_meetups, finished_meetups, self.legacy_stats, season_start
        )
        if team_count == 2:
            winning_counts = extract_winning_counts(finished_meetups)
            team_a, team_b = optimize_teams(
                remaining_players,
                player_scores,
                winning_counts,
                positions,  # type: ignore[arg-type]
                initial_sizes=(initial_sizes[0], initial_sizes[1]),
            )
            groups = [team_a, team_b]
        else:
            groups = list(
                _snake_draft(
                    remaining_players,
                    player_scores,
                    team_count,
                    positions,
                    initial_sizes=initial_sizes,
                )
            )

        return tuple(
            TeamAssignment(
                players=_with_goalkeeper(group, goalkeeper_per_team[i]),
                goalkeeper=goalkeeper_per_team[i],
            )
            for i, group in enumerate(groups)
        )

    def _player_positions(self, players: list[PlayerId]) -> dict[PlayerId, str | None]:
        """Return each player's stored position, or {} if no repository was injected."""
        if self.player_repository is None:
            return {}
        all_players = {p.id: p for p in self.player_repository.find_all()}
        return {pid: all_players[pid].position if pid in all_players else None for pid in players}


def optimize_teams(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
    positions: dict[PlayerId, str | None] | None = None,
    initial_sizes: tuple[int, int] = (0, 0),
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Assign players to two balanced teams using a broad good-candidate pool.

    For normal meetup sizes, every unique partition is scored. The final assignment
    is picked from a weighted pool of good options, so repeated calls preserve
    balance while avoiding the same few local optima every time. ``initial_sizes``
    accounts for members a team already has before this split (e.g. a pre-assigned
    goalkeeper), so the two teams' FINAL sizes (this split plus the handicap)
    differ by at most 1, not just the split itself.
    """
    if len(player_ids) < 2:
        raise ValueError("Need at least 2 players to create teams")

    if positions is None:
        positions = {}

    max_pair_wins = max(winning_counts.values(), default=0)
    if len(player_ids) <= _MAX_EXHAUSTIVE_PLAYERS:
        partitions = _unique_partitions(player_ids, initial_sizes)
    else:
        partitions = _sampled_partitions(player_ids, initial_sizes)

    cost_config: AssignmentCostConfig = (
        player_scores,
        winning_counts,
        max_pair_wins,
        positions,
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


def compute_goalkeeper_scores(
    candidate_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
) -> dict[PlayerId, float]:
    """Return a normalized [0, 1] defensive score per candidate goalkeeper.

    Only counts matches where the candidate was that team's designated
    ``Team.goalkeeper`` for the whole meetup. Fewer goals conceded per match
    scores higher. Uses season data when a candidate has >= _SEASON_MIN_MATCHES
    there, otherwise falls back to full history. Candidates with no such history
    receive the group mean; if nobody has history, everyone gets 0.5.
    """
    averages: dict[PlayerId, float | None] = {}
    for pid in candidate_ids:
        mp_s, conceded_s = _goalkeeper_stats(pid, season_meetups)
        if mp_s >= _SEASON_MIN_MATCHES:
            averages[pid] = conceded_s / mp_s
        else:
            mp_a, conceded_a = _goalkeeper_stats(pid, all_meetups)
            averages[pid] = (conceded_a / mp_a) if mp_a > 0 else None

    known = [(pid, avg) for pid, avg in averages.items() if avg is not None]
    if not known:
        return {pid: 0.5 for pid in candidate_ids}

    known_pids = [pid for pid, _ in known]
    normalized = _normalize([avg for _, avg in known])
    known_scores = {pid: 1.0 - normalized[i] for i, pid in enumerate(known_pids)}

    mean_score = sum(known_scores.values()) / len(known_scores)
    return {pid: known_scores.get(pid, mean_score) for pid in candidate_ids}


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


def _sampled_partitions(
    player_ids: list[PlayerId], initial_sizes: tuple[int, int] = (0, 0)
) -> list[tuple[list[PlayerId], list[PlayerId]]]:
    """Return random unique-ish partitions for player counts too large to exhaustively search."""
    partitions: list[tuple[list[PlayerId], list[PlayerId]]] = []
    seen: set[frozenset[PlayerId]] = set()
    team_a_size = _balanced_team_a_size(len(player_ids), initial_sizes)

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


def _balanced_team_a_size(remaining_count: int, initial_sizes: tuple[int, int]) -> int:
    """Return team A's split size so final sizes (split size + handicap) differ by <=1."""
    total = remaining_count + initial_sizes[0] + initial_sizes[1]
    target_a_total = total // 2
    team_a_size = target_a_total - initial_sizes[0]
    return max(0, min(remaining_count, team_a_size))


def _unique_partitions(
    player_ids: list[PlayerId], initial_sizes: tuple[int, int] = (0, 0)
) -> list[tuple[list[PlayerId], list[PlayerId]]]:
    """Return unique two-team partitions, avoiding mirrored duplicates.

    ``initial_sizes`` is each team's existing member count (e.g. a pre-assigned
    goalkeeper); team A's split size is chosen so the FINAL sizes (split size
    plus handicap) differ by at most 1.
    """
    team_a_size = _balanced_team_a_size(len(player_ids), initial_sizes)
    if team_a_size == 0:
        return []

    partitions: list[tuple[list[PlayerId], list[PlayerId]]] = []

    def _append_partition(team_a: list[PlayerId]) -> None:
        team_a_set = set(team_a)
        team_b = [pid for pid in player_ids if pid not in team_a_set]
        partitions.append((team_a, team_b))

    if team_a_size == len(player_ids) - team_a_size:
        anchor = player_ids[0]
        for rest in itertools.combinations(player_ids[1:], team_a_size - 1):
            _append_partition([anchor, *rest])
    else:
        for combination in itertools.combinations(player_ids, team_a_size):
            _append_partition(list(combination))

    return partitions


AssignmentCostConfig = tuple[
    dict[PlayerId, float], dict[tuple[str, str], int], int, dict[PlayerId, str | None]
]


def _assignment_cost(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    config: AssignmentCostConfig,
) -> float:
    """Return total assignment cost: strength balance plus composition diversity."""
    player_scores, winning_counts, max_pair_wins, positions = config
    balance_cost = abs(
        _team_strength(team_a, player_scores) - _team_strength(team_b, player_scores)
    )
    pair_cost = _pair_repeat_penalty(team_a, team_b, winning_counts, max_pair_wins)
    position_cost = _position_imbalance_penalty(team_a, team_b, positions) if positions else 0.0
    return balance_cost + (_PAIR_WEIGHT * pair_cost) + (_POSITION_WEIGHT * position_cost)


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


def _position_imbalance_penalty(
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    positions: dict[PlayerId, str | None],
) -> float:
    """Return a normalized outfield-position-mix imbalance penalty between two teams."""

    def _counts(team: list[PlayerId]) -> dict[str, int]:
        return {
            pos: sum(1 for pid in team if positions.get(pid) == pos) for pos in _OUTFIELD_POSITIONS
        }

    counts_a, counts_b = _counts(team_a), _counts(team_b)
    total = sum(counts_a.values()) + sum(counts_b.values())
    if total == 0:
        return 0.0
    return sum(abs(counts_a[pos] - counts_b[pos]) for pos in _OUTFIELD_POSITIONS) / total


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


def _goalkeeper_stats(player_id: PlayerId, meetups: list[Meetup]) -> tuple[int, int]:
    """Return (matches played as designated goalkeeper, goals conceded in them)."""
    matches = conceded = 0
    for meetup in meetups:
        if meetup.teams is None:
            continue
        team = next((t for t in meetup.teams if t.goalkeeper == player_id), None)
        if team is None:
            continue
        for match in meetup.matches:
            if match.result is None or team not in match.teams_playing:
                continue
            index = match.teams_playing.index(team)
            conceded += match.result.score_b if index == 0 else match.result.score_a
            matches += 1
    return matches, conceded


def _with_goalkeeper(group: list[PlayerId], goalkeeper: PlayerId | None) -> list[PlayerId]:
    """Return group with its pre-assigned goalkeeper included as a team member."""
    if goalkeeper is None:
        return group
    return [goalkeeper, *group]


def _assign_goalkeepers(
    players: list[PlayerId],
    positions: dict[PlayerId, str | None],
    gk_scores: dict[PlayerId, float],
    team_count: int,
) -> tuple[list[PlayerId | None], list[PlayerId]]:
    """Distribute portero-tagged players one per team via a score-weighted lottery.

    Returns (goalkeeper_per_team, remaining_players): goalkeeper_per_team has
    team_count entries (None for a team that got no goalkeeper); remaining_players
    is every input player not assigned as a goalkeeper, for the rest of the
    balancing to treat as ordinary players. The order in which teams are
    considered is shuffled, so which team gets a goalkeeper first is randomized
    too, not always team index 0.
    """
    remaining_candidates = sorted(
        (pid for pid in players if positions.get(pid) == "portero"),
        key=lambda pid: gk_scores.get(pid, 0.5),
        reverse=True,
    )
    team_indices = list(range(team_count))
    random.shuffle(team_indices)
    goalkeeper_per_team: list[PlayerId | None] = [None] * team_count
    for team_index in team_indices:
        if not remaining_candidates:
            break
        weights = [
            1.0 / (rank + _DRAFT_PICK_TEMPERATURE) for rank in range(len(remaining_candidates))
        ]
        pid = random.choices(remaining_candidates, weights=weights, k=1)[0]
        remaining_candidates.remove(pid)
        goalkeeper_per_team[team_index] = pid

    assigned = {pid for pid in goalkeeper_per_team if pid is not None}
    remaining_players = [pid for pid in players if pid not in assigned]
    return goalkeeper_per_team, remaining_players


def _snake_draft(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    team_count: int,
    positions: dict[PlayerId, str | None] | None = None,
    initial_sizes: list[int] | None = None,
) -> tuple[list[PlayerId], ...]:
    """Distribute players into team_count groups via a weighted-lottery draft.

    At each pick, the team with the fewest total members so far -- counting any
    ``initial_sizes`` handicap, e.g. a pre-assigned goalkeeper already on that
    team -- gets the next player, with ties broken at random, so final team
    sizes stay balanced (differ by at most 1) regardless of how many teams
    already have a head start. Instead of deterministically taking the single
    highest-scored remaining player (which reproduces the exact same grouping
    every time whenever players have distinct historical scores, not just when
    they're tied), the next player is drawn from a weighted lottery favoring
    higher-ranked remaining players -- strong players are still likely to be
    spread across teams early, but which specific player is picked, and thus
    the final grouping, varies between calls. When positions are known, a
    candidate whose outfield position the picking team doesn't have yet gets
    its weight boosted, spreading tagged positions across teams too.
    """
    positions = positions or {}
    initial_sizes = initial_sizes or [0] * team_count
    remaining = sorted(player_ids, key=lambda pid: player_scores.get(pid, 0.5), reverse=True)
    teams: list[list[PlayerId]] = [[] for _ in range(team_count)]
    while remaining:
        totals = [len(teams[i]) + initial_sizes[i] for i in range(team_count)]
        smallest = min(totals)
        index = random.choice([i for i, total in enumerate(totals) if total == smallest])
        weights = [1.0 / (rank + _DRAFT_PICK_TEMPERATURE) for rank in range(len(remaining))]
        weights = _apply_position_fit_boost(weights, remaining, teams[index], positions)
        pid = random.choices(remaining, weights=weights, k=1)[0]
        remaining.remove(pid)
        teams[index].append(pid)
    return tuple(teams)


def _apply_position_fit_boost(
    weights: list[float],
    remaining: list[PlayerId],
    team_so_far: list[PlayerId],
    positions: dict[PlayerId, str | None],
) -> list[float]:
    """Boost the weight of candidates whose outfield position the picking team lacks."""
    if not positions:
        return weights
    team_positions = {positions.get(pid) for pid in team_so_far}

    def _lacks_position(pid: PlayerId) -> bool:
        position = positions.get(pid)
        return position in _OUTFIELD_POSITIONS and position not in team_positions

    return [
        w * _POSITION_FIT_BOOST if _lacks_position(pid) else w
        for w, pid in zip(weights, remaining)
    ]
