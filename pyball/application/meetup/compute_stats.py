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
"""Compute match statistics use case."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from pyball.domain.meetup.match_stats import winning_pair_counts
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.meetup.season import season_scope
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure.persistence import LegacyStats


@dataclass
class _PlayerCounters:
    goals: int = 0
    assists: int = 0
    own_goals: int = 0
    mp: int = 0
    w: int = 0
    d: int = 0
    losses: int = 0


@dataclass
class PlayerStats:  # pylint: disable=too-many-instance-attributes
    """Aggregated statistics for a single player."""

    player_id: str
    player_name: str
    goals: int
    assists: int
    own_goals: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    points_rank_delta: int | None
    goals_rank_delta: int | None
    assists_rank_delta: int | None

    @property
    def points(self) -> int:
        """Return league points: win=3, draw=1, loss=0."""
        return self.wins * 3 + self.draws


@dataclass
class ChemistryPair:
    """A scorer+assistant pair and how many times they combined."""

    scorer_name: str
    assistant_name: str
    count: int


@dataclass
class WinningPair:
    """A pair of players who won together most often."""

    player_a_name: str
    player_b_name: str
    count: int


@dataclass
class StatsScopedReport:
    """Statistics for a single time scope (season or all-time)."""

    players: list[PlayerStats]
    chemistry: list[ChemistryPair]
    winning_pairs: list[WinningPair] = field(default_factory=list)


@dataclass
class StatsReport:
    """Full statistics report with season and all-time scopes."""

    season: StatsScopedReport
    all_time: StatsScopedReport
    latest_match_date: datetime | None = None


def _points_from_counters(counters: _PlayerCounters) -> int:
    """Return league points from a raw counter."""
    return counters.w * 3 + counters.d


def _aggregate(
    meetups: list,
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> tuple[dict[str, _PlayerCounters], dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    """Aggregate raw stats from a list of meetups.

    Returns:
        Tuple of (player_data, chemistry_counts, winning_counts) where
        player_data maps player_id to stat counters, chemistry_counts maps
        (scorer_id, assistant_id) to occurrence count, and winning_counts maps
        sorted (player_id_a, player_id_b) to co-win count.
    """
    player_data: dict[str, _PlayerCounters] = {}
    chemistry_counts: dict[tuple[str, str], int] = {}

    for meetup in meetups:
        for match in meetup.matches:
            _aggregate_match(match, player_data, chemistry_counts)

    if legacy_stats:
        for pid, data in player_data.items():
            data.assists += legacy_stats.get_assists(pid, from_date)
        for pid in legacy_stats.all_players():
            if pid not in player_data:
                leg_assists = legacy_stats.get_assists(pid, from_date)
                if leg_assists > 0:
                    player_data[pid] = _PlayerCounters()
                    player_data[pid].assists = leg_assists

    winning_counts = winning_pair_counts(meetups)
    return player_data, chemistry_counts, winning_counts


def _aggregate_match(
    match,
    player_data: dict[str, _PlayerCounters],
    chemistry_counts: dict[tuple[str, str], int],
) -> None:
    """Aggregate one match's per-team win/draw/loss and goal-event stats into the counters."""
    if match.result is None:
        return

    winner_index = match.result.winner_index()

    for i, team in enumerate(match.teams_playing):
        team_wins = i == winner_index
        team_draws = winner_index is None

        for player_id in team.players:
            pid = str(player_id.value)
            if pid not in player_data:
                player_data[pid] = _PlayerCounters()
            player_data[pid].mp += 1
            if team_wins:
                player_data[pid].w += 1
            elif team_draws:
                player_data[pid].d += 1
            else:
                player_data[pid].losses += 1

    for event in match.result.events:
        _aggregate_goal_event(event, player_data, chemistry_counts)


def _aggregate_goal_event(
    event,
    player_data: dict[str, _PlayerCounters],
    chemistry_counts: dict[tuple[str, str], int],
) -> None:
    """Aggregate a single goal event's scorer/assistant/chemistry stats into the counters."""
    scorer_id = str(event.scorer_id.value)
    if scorer_id not in player_data:
        player_data[scorer_id] = _PlayerCounters()

    if event.is_own_goal:
        player_data[scorer_id].own_goals += 1
        return

    player_data[scorer_id].goals += 1
    if event.assistant_id is None:
        return

    assistant_id = str(event.assistant_id.value)
    if assistant_id not in player_data:
        player_data[assistant_id] = _PlayerCounters()
    player_data[assistant_id].assists += 1
    pair_chem = (scorer_id, assistant_id)
    chemistry_counts[pair_chem] = chemistry_counts.get(pair_chem, 0) + 1


def _rank_from_prev(
    prev_data: dict[str, _PlayerCounters],
    eligible: Callable[[_PlayerCounters], bool],
    key_fn: Callable[[str], tuple],
) -> dict[str, int]:
    """Return a {player_id: rank} dict for eligible players in prev_data."""
    ranked = sorted(
        [pid for pid in prev_data if eligible(prev_data[pid])],
        key=key_fn,
    )
    return {pid: i + 1 for i, pid in enumerate(ranked)}


def _apply_deltas(
    players: list[PlayerStats],
    prev_rank: dict[str, int],
    attr: str,
) -> None:
    """Assign rank deltas by comparing each player's current position to prev_rank."""
    for i, player in enumerate(players):
        if player.player_id in prev_rank:
            setattr(player, attr, prev_rank[player.player_id] - (i + 1))


def _build_scoped_report(
    meetups: list,
    player_names: dict[str, str],
    prev_meetups: list | None = None,
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> StatsScopedReport:
    """Build a StatsScopedReport, computing rank deltas from prev_meetups if provided."""
    player_data, chemistry_counts, winning_counts = _aggregate(meetups, legacy_stats, from_date)

    stats_list = [
        PlayerStats(
            player_id=pid,
            player_name=player_names.get(pid, pid),
            goals=d.goals,
            assists=d.assists,
            own_goals=d.own_goals,
            matches_played=d.mp,
            wins=d.w,
            draws=d.d,
            losses=d.losses,
            points_rank_delta=None,
            goals_rank_delta=None,
            assists_rank_delta=None,
        )
        for pid, d in player_data.items()
    ]
    stats_list.sort(key=lambda p: (-p.points, -p.wins, -p.goals, -p.assists, p.player_name))

    if prev_meetups is not None:
        prev_data, _, _ = _aggregate(prev_meetups, legacy_stats, from_date)

        prev_pts_rank = _rank_from_prev(
            prev_data,
            eligible=lambda c: _points_from_counters(c) > 0,
            key_fn=lambda pid: (
                -_points_from_counters(prev_data[pid]),
                -prev_data[pid].w,
                -prev_data[pid].goals,
                -prev_data[pid].assists,
                player_names.get(pid, pid),
            ),
        )
        _apply_deltas(
            [p for p in stats_list if p.points > 0],
            prev_pts_rank,
            "points_rank_delta",
        )

        prev_goals_rank = _rank_from_prev(
            prev_data,
            eligible=lambda c: c.goals > 0,
            key_fn=lambda pid: (-prev_data[pid].goals, player_names.get(pid, pid)),
        )
        _apply_deltas(
            sorted(
                [p for p in stats_list if p.goals > 0],
                key=lambda p: (-p.goals, p.player_name),
            ),
            prev_goals_rank,
            "goals_rank_delta",
        )

        prev_assists_rank = _rank_from_prev(
            prev_data,
            eligible=lambda c: c.assists > 0,
            key_fn=lambda pid: (-prev_data[pid].assists, player_names.get(pid, pid)),
        )
        _apply_deltas(
            sorted(
                [p for p in stats_list if p.assists > 0],
                key=lambda p: (-p.assists, p.player_name),
            ),
            prev_assists_rank,
            "assists_rank_delta",
        )

    chemistry = sorted(
        [
            ChemistryPair(
                scorer_name=player_names.get(scorer_id, scorer_id),
                assistant_name=player_names.get(assistant_id, assistant_id),
                count=cnt,
            )
            for (scorer_id, assistant_id), cnt in chemistry_counts.items()
        ],
        key=lambda c: c.count,
        reverse=True,
    )[:10]

    winning_pairs = sorted(
        [
            WinningPair(
                player_a_name=player_names.get(pid_a, pid_a),
                player_b_name=player_names.get(pid_b, pid_b),
                count=cnt,
            )
            for (pid_a, pid_b), cnt in winning_counts.items()
        ],
        key=lambda wp: wp.count,
        reverse=True,
    )[:5]

    return StatsScopedReport(players=stats_list, chemistry=chemistry, winning_pairs=winning_pairs)


class ComputeStats:
    """Use case for computing post-match player statistics."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
        legacy_stats: LegacyStats | None = None,
    ) -> None:
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository
        self.legacy_stats = legacy_stats

    def execute(self) -> StatsReport:
        """Compute and return season and all-time statistics.

        Returns:
            StatsReport with season and all_time StatsScopedReports.
        """
        all_meetups = self.meetup_repository.find_all()
        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        scope = season_scope(all_meetups)
        finished, season_meetups = scope.finished, scope.season_meetups

        latest_match_date: datetime | None = None
        if finished:
            latest = max(finished, key=lambda m: m.date)
            prev_all = [m for m in finished if m is not latest]
            prev_season = [m for m in season_meetups if m is not latest]
            latest_match_date = latest.date
        else:
            prev_all = None
            prev_season = None

        return StatsReport(
            season=_build_scoped_report(
                season_meetups, player_names, prev_season, self.legacy_stats, scope.season_start
            ),
            all_time=_build_scoped_report(finished, player_names, prev_all, self.legacy_stats),
            latest_match_date=latest_match_date,
        )
