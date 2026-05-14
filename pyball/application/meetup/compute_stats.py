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

import itertools
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure.persistence import LegacyStats


@dataclass
class _PlayerCounters:
    goals: int = 0
    assists: int = 0
    mp: int = 0
    w: int = 0
    d: int = 0
    l: int = 0


@dataclass
class PlayerStats:  # pylint: disable=too-many-instance-attributes
    """Aggregated statistics for a single player."""

    player_id: str
    player_name: str
    goals: int
    assists: int
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


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)


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
    winning_counts: dict[tuple[str, str], int] = {}

    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue

        score_a = meetup.result.score_a
        score_b = meetup.result.score_b

        for team in meetup.teams:
            team_wins = (team.name == "A" and score_a > score_b) or (
                team.name == "B" and score_b > score_a
            )
            team_draws = score_a == score_b

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
                    player_data[pid].l += 1

            if team_wins:
                for pid_a, pid_b in itertools.combinations(team.players, 2):
                    a, b = sorted([str(pid_a.value), str(pid_b.value)])
                    winning_counts[(a, b)] = winning_counts.get((a, b), 0) + 1

        for event in meetup.result.events:
            scorer_id = str(event.scorer_id.value)
            if scorer_id not in player_data:
                player_data[scorer_id] = _PlayerCounters()
            player_data[scorer_id].goals += 1

            if event.assistant_id is not None:
                assistant_id = str(event.assistant_id.value)
                if assistant_id not in player_data:
                    player_data[assistant_id] = _PlayerCounters()
                player_data[assistant_id].assists += 1
                pair_chem = (scorer_id, assistant_id)
                chemistry_counts[pair_chem] = chemistry_counts.get(pair_chem, 0) + 1

    if legacy_stats:
        for pid, data in player_data.items():
            if from_date is not None:
                data.assists += legacy_stats.get_assists_since(pid, from_date)
            else:
                data.assists += legacy_stats.get(pid).get("assists", 0)
        for pid in legacy_stats.all_players():
            if pid not in player_data:
                leg_assists = (
                    legacy_stats.get_assists_since(pid, from_date)
                    if from_date is not None
                    else legacy_stats.get(pid).get("assists", 0)
                )
                if leg_assists > 0:
                    player_data[pid] = _PlayerCounters()
                    player_data[pid].assists = leg_assists

    return player_data, chemistry_counts, winning_counts


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
            matches_played=d.mp,
            wins=d.w,
            draws=d.d,
            losses=d.l,
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

        today = date.today()
        season_start = _season_start(today)

        finished = [m for m in all_meetups if m.result is not None]
        season_meetups = [m for m in finished if m.date.date() >= season_start]

        latest_match_date: datetime | None = None
        if finished:
            latest = max(finished, key=lambda m: m.date)
            prev_all = [m for m in finished if m is not latest]
            prev_season = [m for m in season_meetups if m is not latest]
            latest_match_date = latest.date
        else:
            prev_all = None
            prev_season = None

        season_start_dt = datetime.combine(season_start, datetime.min.time())

        return StatsReport(
            season=_build_scoped_report(
                season_meetups, player_names, prev_season, self.legacy_stats, season_start_dt
            ),
            all_time=_build_scoped_report(finished, player_names, prev_all, self.legacy_stats),
            latest_match_date=latest_match_date,
        )
