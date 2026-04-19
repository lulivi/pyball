"""Balanced team creation: player scoring and team optimization."""

from __future__ import annotations

from pyball.domain.meetup.models import Meetup, PlayerId

_SEASON_MIN_MATCHES = 3
_W_GOALS = 0.40
_W_ASSISTS = 0.30
_W_WINS = 0.30
_PAIR_WEIGHT = 1.0
_ITERATIONS = 500


def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
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
    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp


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
) -> dict[PlayerId, float]:
    """Return a normalized [0, 1] strength score for each player.

    Uses season data when a player has >= _SEASON_MIN_MATCHES there, otherwise
    falls back to full history. Players with no history receive the group mean.
    """
    components: dict[PlayerId, tuple[float, float, float] | None] = {}
    for pid in player_ids:
        mp_s, gpm_s, apm_s, wr_s = _player_stats(pid, season_meetups)
        if mp_s >= _SEASON_MIN_MATCHES:
            components[pid] = (gpm_s, apm_s, wr_s)
        else:
            mp_a, gpm_a, apm_a, wr_a = _player_stats(pid, all_meetups)
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
