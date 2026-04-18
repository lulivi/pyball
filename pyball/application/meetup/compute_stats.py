"""Compute match statistics use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


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
class StatsScopedReport:
    """Statistics for a single time scope (season or all-time)."""

    players: list[PlayerStats]
    chemistry: list[ChemistryPair]


@dataclass
class StatsReport:
    """Full statistics report with season and all-time scopes."""

    season: StatsScopedReport
    all_time: StatsScopedReport


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)


def _empty_counters() -> dict:
    """Return a zeroed stat counter dict for a player."""
    return {"goals": 0, "assists": 0, "mp": 0, "w": 0, "d": 0, "l": 0}


def _points_from_counters(counters: dict) -> int:
    """Return league points from a raw counter dict."""
    return counters["w"] * 3 + counters["d"]


def _aggregate(
    meetups: list,
) -> tuple[dict[str, dict], dict[tuple[str, str], int]]:
    """Aggregate raw stats from a list of meetups.

    Returns:
        Tuple of (player_data, chemistry_counts) where player_data maps
        player_id to stat counters and chemistry_counts maps (scorer_id, assistant_id)
        to occurrence count.
    """
    player_data: dict[str, dict] = {}
    chemistry_counts: dict[tuple[str, str], int] = {}

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
                    player_data[pid] = _empty_counters()
                player_data[pid]["mp"] += 1
                if team_wins:
                    player_data[pid]["w"] += 1
                elif team_draws:
                    player_data[pid]["d"] += 1
                else:
                    player_data[pid]["l"] += 1

        for event in meetup.result.events:
            scorer_id = str(event.scorer_id.value)
            if scorer_id not in player_data:
                player_data[scorer_id] = _empty_counters()
            player_data[scorer_id]["goals"] += 1

            if event.assistant_id is not None:
                assistant_id = str(event.assistant_id.value)
                if assistant_id not in player_data:
                    player_data[assistant_id] = _empty_counters()
                player_data[assistant_id]["assists"] += 1
                pair = (scorer_id, assistant_id)
                chemistry_counts[pair] = chemistry_counts.get(pair, 0) + 1

    return player_data, chemistry_counts


def _build_scoped_report(
    meetups: list,
    player_names: dict[str, str],
    prev_meetups: list | None = None,
) -> StatsScopedReport:
    """Build a StatsScopedReport, computing rank deltas from prev_meetups if provided."""
    player_data, chemistry_counts = _aggregate(meetups)

    stats_list = [
        PlayerStats(
            player_id=pid,
            player_name=player_names.get(pid, pid),
            goals=d["goals"],
            assists=d["assists"],
            matches_played=d["mp"],
            wins=d["w"],
            draws=d["d"],
            losses=d["l"],
            points_rank_delta=None,
            goals_rank_delta=None,
            assists_rank_delta=None,
        )
        for pid, d in player_data.items()
    ]
    stats_list.sort(key=lambda p: (-p.points, p.player_name))

    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups)

        prev_pts_ranked = sorted(
            [pid for pid, d in prev_data.items() if _points_from_counters(d) > 0],
            key=lambda pid: (-_points_from_counters(prev_data[pid]), player_names.get(pid, pid)),
        )
        prev_pts_rank = {pid: i + 1 for i, pid in enumerate(prev_pts_ranked)}
        for i, player in enumerate([p for p in stats_list if p.points > 0]):
            if player.player_id in prev_pts_rank:
                player.points_rank_delta = prev_pts_rank[player.player_id] - (i + 1)

        prev_goals_ranked = sorted(
            [pid for pid, d in prev_data.items() if d["goals"] > 0],
            key=lambda pid: (-prev_data[pid]["goals"], player_names.get(pid, pid)),
        )
        prev_goals_rank = {pid: i + 1 for i, pid in enumerate(prev_goals_ranked)}
        current_goals = sorted(
            [p for p in stats_list if p.goals > 0],
            key=lambda p: (-p.goals, p.player_name),
        )
        for i, player in enumerate(current_goals):
            if player.player_id in prev_goals_rank:
                player.goals_rank_delta = prev_goals_rank[player.player_id] - (i + 1)

        prev_assists_ranked = sorted(
            [pid for pid, d in prev_data.items() if d["assists"] > 0],
            key=lambda pid: (-prev_data[pid]["assists"], player_names.get(pid, pid)),
        )
        prev_assists_rank = {pid: i + 1 for i, pid in enumerate(prev_assists_ranked)}
        current_assists = sorted(
            [p for p in stats_list if p.assists > 0],
            key=lambda p: (-p.assists, p.player_name),
        )
        for i, player in enumerate(current_assists):
            if player.player_id in prev_assists_rank:
                player.assists_rank_delta = prev_assists_rank[player.player_id] - (i + 1)

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

    return StatsScopedReport(players=stats_list, chemistry=chemistry)


class ComputeStats:
    """Use case for computing post-match player statistics."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ) -> None:
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

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

        if finished:
            latest = max(finished, key=lambda m: m.date)
            prev_all = [m for m in finished if m is not latest]
            prev_season = [m for m in season_meetups if m is not latest]
        else:
            prev_all = None
            prev_season = None

        return StatsReport(
            season=_build_scoped_report(season_meetups, player_names, prev_season),
            all_time=_build_scoped_report(finished, player_names, prev_all),
        )
