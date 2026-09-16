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
"""Format match summary use case."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pyball.domain.meetup.models import GoalEvent, Match, Meetup, Team
from pyball.infrastructure.persistence.legacy_stats import LegacyStats

_ROUND_SEPARATOR = "➖➖➖➖➖➖➖➖➖➖"


class FormatMatchSummary:
    """Build the plain-text post-match summary for a finished meetup."""

    def execute(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        meetup: Meetup,
        player_names: dict[str, str],
        team_colors: tuple[str, ...] = ("blanco", "negro"),
        team_emojis: tuple[str, ...] = ("⚪", "⚫"),
        date_label: str | None = None,
        legacy_stats: LegacyStats | None = None,
    ) -> str:
        """Return the summary string, ready to paste into a chat.

        For a classic (2-team) meetup, renders the score block for its one match
        followed by a chronological events list. For a triangular (3-team) meetup,
        renders each team's roster with session-wide per-player stats and
        win/draw/loss record first, then one header-plus-events block per round
        played, in order.

        Args:
            meetup: A finished meetup with matches and teams.
            player_names: Mapping of str(player_id.value) to display name.
            team_colors: Color name per team (capitalized as display name).
            team_emojis: Circle emoji per team.
            date_label: Pre-formatted date string (e.g. "18 Mayo"). If None,
                defaults to meetup.date formatted as "YYYY-MM-DD HH:MM".
            legacy_stats: Optional legacy statistics. When provided, assists for
                players with no event assists are read from it for this match date.

        Returns:
            Multi-line summary message string.
        """
        if not meetup.matches:
            raise ValueError("Meetup has no matches yet")
        if meetup.teams is None:
            raise ValueError("Meetup has no teams yet")

        is_triangular = len(meetup.teams) == 3
        label = date_label or meetup.date.strftime("%Y-%m-%d %H:%M")
        lines = [f"🎉 *Convocatoria: {label}*"]
        if meetup.location:
            lines.append(f"📍 *{meetup.location}*")

        if is_triangular:
            lines.append("")
            lines.append("*EQUIPOS:*")
            for index, team in enumerate(meetup.teams):
                lines.append("")
                lines.extend(
                    _team_standing_block(
                        team,
                        index,
                        meetup.matches,
                        player_names,
                        team_colors,
                        team_emojis,
                        legacy_stats,
                        meetup.date,
                    )
                )

        lines.append("")
        lines.append("*RESULTADO:*")

        played_a_round = False
        for match in meetup.matches:
            if match.result is None:
                continue
            lines.append("")
            if played_a_round:
                lines.append(_ROUND_SEPARATOR)
                lines.append("")
            if is_triangular:
                lines.extend(
                    _round_block(match, meetup.teams, team_colors, team_emojis, player_names)
                )
            else:
                lines.extend(
                    _match_block(
                        match,
                        meetup.teams,
                        player_names,
                        team_colors,
                        team_emojis,
                        legacy_stats,
                        meetup.date,
                    )
                )
            played_a_round = True

        return "\n".join(lines)


def _match_block(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    match: Match,
    all_teams: list[Team],
    player_names: dict[str, str],
    team_colors: tuple[str, ...],
    team_emojis: tuple[str, ...],
    legacy_stats: LegacyStats | None,
    meetup_date: datetime,
) -> list[str]:
    """Return the summary lines for a classic match: two team blocks plus events.

    Colors/emojis are indexed by each team's position in the meetup's overall team
    list (not its position within this match), so a team keeps the same color
    across every round of a triangular meetup.
    """
    result = match.result
    assert result is not None

    goals, own_goals, assists = _aggregate_stats(result.events)
    if legacy_stats is not None:
        all_pids = [str(pid.value) for team in match.teams_playing for pid in team.players]
        _apply_legacy_assists(assists, all_pids, legacy_stats, meetup_date)

    lines: list[str] = []
    for i, team in enumerate(match.teams_playing):
        if i > 0:
            lines.append("")
        score = result.score_a if i == 0 else result.score_b
        lines.append(_team_score_header(team, all_teams, team_colors, team_emojis, score))
        team_ids = [str(pid.value) for pid in team.players]
        goalkeeper_id = str(team.goalkeeper.value) if team.goalkeeper else None
        lines.extend(
            _player_line(pid, player_names, goals, own_goals, assists, goalkeeper_id)
            for pid in team_ids
        )

    if result.events:
        lines.append("")
        lines.append("*GOLES:*")
        lines.extend(_events_block(result.events, player_names))

    return lines


def _round_block(
    match: Match,
    all_teams: list[Team],
    team_colors: tuple[str, ...],
    team_emojis: tuple[str, ...],
    player_names: dict[str, str],
) -> list[str]:
    """Return a triangular round's lines: two score headers plus that round's events.

    Player rosters are not repeated here -- they're shown once, with session-wide
    stats, in the "*EQUIPOS:*" section.
    """
    result = match.result
    assert result is not None

    lines: list[str] = []
    for i, team in enumerate(match.teams_playing):
        if i > 0:
            lines.append("")
        score = result.score_a if i == 0 else result.score_b
        lines.append(_team_score_header(team, all_teams, team_colors, team_emojis, score))

    if result.events:
        lines.append("")
        lines.extend(_events_block(result.events, player_names))

    return lines


def _team_standing_block(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    team: Team,
    index: int,
    matches: list[Match],
    player_names: dict[str, str],
    team_colors: tuple[str, ...],
    team_emojis: tuple[str, ...],
    legacy_stats: LegacyStats | None,
    meetup_date: datetime,
) -> list[str]:
    """Return this team's win/draw/loss record, plus its roster with session stats."""
    wins, draws, losses = _team_record(team, matches)
    color = team_colors[index] if index < len(team_colors) else None
    name = color.capitalize() if color is not None else team.name
    emoji = team_emojis[index] if index < len(team_emojis) else ""
    lines = [f"{emoji} *{name}* ({wins}V {draws}E {losses}D)"]

    all_events = [
        event for match in matches if match.result is not None for event in match.result.events
    ]
    goals, own_goals, assists = _aggregate_stats(all_events)
    if legacy_stats is not None:
        team_ids = [str(pid.value) for pid in team.players]
        _apply_legacy_assists(assists, team_ids, legacy_stats, meetup_date)

    goalkeeper_id = str(team.goalkeeper.value) if team.goalkeeper else None
    lines.extend(
        _player_line(str(pid.value), player_names, goals, own_goals, assists, goalkeeper_id)
        for pid in team.players
    )
    return lines


def _team_record(team: Team, matches: list[Match]) -> tuple[int, int, int]:
    """Return (wins, draws, losses) for team across all of its finished matches."""
    wins = draws = losses = 0
    for match in matches:
        if match.result is None or team not in match.teams_playing:
            continue
        index = match.teams_playing.index(team)
        score = match.result.score_a if index == 0 else match.result.score_b
        opponent_score = match.result.score_b if index == 0 else match.result.score_a
        if score > opponent_score:
            wins += 1
        elif score < opponent_score:
            losses += 1
        else:
            draws += 1
    return wins, draws, losses


def _team_score_header(
    team: Team,
    all_teams: list[Team],
    team_colors: tuple[str, ...],
    team_emojis: tuple[str, ...],
    score: int,
) -> str:
    """Return a team's bold "{emoji} {Name} - {score}" header line."""
    team_index = all_teams.index(team)
    color = team_colors[team_index] if team_index < len(team_colors) else None
    name = color.capitalize() if color is not None else team.name
    emoji = team_emojis[team_index] if team_index < len(team_emojis) else ""
    return f"{emoji} *{name} - {score}*"


def _events_block(events: Sequence[GoalEvent], player_names: dict[str, str]) -> list[str]:
    """Return one chronological "- emoji minute' scorer (extra)" line per event."""
    lines: list[str] = []
    for event in events:
        scorer = player_names.get(str(event.scorer_id.value), str(event.scorer_id.value))
        minutes = event.timestamp.strftime("%M")
        if event.is_own_goal:
            lines.append(f"  - 🥅 {minutes}' {scorer} (en propia)")
        elif event.assistant_id:
            assistant = player_names.get(
                str(event.assistant_id.value), str(event.assistant_id.value)
            )
            lines.append(f"  - ⚽ {minutes}' {scorer} (asist. {assistant})")
        else:
            lines.append(f"  - ⚽ {minutes}' {scorer}")
    return lines


def _aggregate_stats(
    events: Sequence[GoalEvent],
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Return (goals, own_goals, assists) count-by-player-id dicts for events."""
    goals: dict[str, int] = {}
    own_goals: dict[str, int] = {}
    assists: dict[str, int] = {}
    for event in events:
        sid = str(event.scorer_id.value)
        if event.is_own_goal:
            own_goals[sid] = own_goals.get(sid, 0) + 1
        else:
            goals[sid] = goals.get(sid, 0) + 1
            if event.assistant_id:
                aid = str(event.assistant_id.value)
                assists[aid] = assists.get(aid, 0) + 1
    return goals, own_goals, assists


def _apply_legacy_assists(
    assists: dict[str, int],
    pids: list[str],
    legacy_stats: LegacyStats,
    meetup_date: datetime,
) -> None:
    """Fill in legacy-stats assist counts for players with no event assists."""
    for pid in pids:
        if assists.get(pid, 0) == 0:
            legacy_count = legacy_stats.get_assists_for_match(pid, meetup_date)
            if legacy_count:
                assists[pid] = legacy_count


def _player_line(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    pid: str,
    player_names: dict[str, str],
    goals: dict[str, int],
    own_goals: dict[str, int],
    assists: dict[str, int],
    goalkeeper_id: str | None = None,
) -> str:
    """Return this player's roster line, prefixed with 🧤 if they're the goalkeeper."""
    name = player_names.get(pid, pid)
    stats = "⚽" * goals.get(pid, 0) + "🥅" * own_goals.get(pid, 0) + "🅰️" * assists.get(pid, 0)
    prefix = "🧤 " if pid == goalkeeper_id else ""
    return prefix + name + (" " + stats if stats else "")
