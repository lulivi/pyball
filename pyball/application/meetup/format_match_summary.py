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

from datetime import datetime

from pyball.domain.meetup.models import Match, Meetup, Team
from pyball.infrastructure.persistence.legacy_stats import LegacyStats


class FormatMatchSummary:
    """Build the WhatsApp-format post-match summary for a finished meetup."""

    def execute(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        meetup: Meetup,
        player_names: dict[str, str],
        team_colors: tuple[str, ...] = ("blanco", "negro"),
        team_emojis: tuple[str, ...] = ("⚪", "⚫"),
        date_label: str | None = None,
        legacy_stats: LegacyStats | None = None,
    ) -> str:
        """Return the WhatsApp-ready summary string.

        For a classic (2-team) meetup, renders one score block per team. For a
        triangular (3-team) meetup, renders one score block per round played,
        in order, so every match result appears in the summary.

        Args:
            meetup: A finished meetup with matches and teams.
            player_names: Mapping of str(player_id.value) to display name.
            team_colors: Color name per team (capitalized as display name).
            team_emojis: Circle emoji per team.
            date_label: Pre-formatted date string (e.g. "18 Mayo"). If None,
                derived from meetup.date using the current locale.
            legacy_stats: Optional legacy statistics. When provided, assists for
                players with no event assists are read from it for this match date.

        Returns:
            Multi-line WhatsApp message string.
        """
        if not meetup.matches:
            raise ValueError("Meetup has no matches yet")
        if meetup.teams is None:
            raise ValueError("Meetup has no teams yet")

        label = date_label or meetup.date.strftime("%-d %B").title()
        lines = ["⚽ Día de Partido ⚽", f"🗓 {label}", "", "*RESULTADO:*"]

        for match in meetup.matches:
            if match.result is None:
                continue
            lines.append("")
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
    """Return the summary lines for a single match: two team blocks with scorers.

    Colors/emojis are indexed by each team's position in the meetup's overall team
    list (not its position within this match), so a team keeps the same color
    across every round of a triangular meetup.
    """
    result = match.result
    assert result is not None

    goals: dict[str, int] = {}
    own_goals: dict[str, int] = {}
    assists: dict[str, int] = {}
    for event in result.events:
        sid = str(event.scorer_id.value)
        if event.is_own_goal:
            own_goals[sid] = own_goals.get(sid, 0) + 1
        else:
            goals[sid] = goals.get(sid, 0) + 1
            if event.assistant_id:
                aid = str(event.assistant_id.value)
                assists[aid] = assists.get(aid, 0) + 1

    if legacy_stats is not None:
        all_pids = [str(pid.value) for team in match.teams_playing for pid in team.players]
        for pid in all_pids:
            if assists.get(pid, 0) == 0:
                legacy_count = legacy_stats.get_assists_for_match(pid, meetup_date)
                if legacy_count:
                    assists[pid] = legacy_count

    lines: list[str] = []
    for i, team in enumerate(match.teams_playing):
        if i > 0:
            lines.append("")
        score = result.score_a if i == 0 else result.score_b
        team_index = all_teams.index(team)
        color = team_colors[team_index] if team_index < len(team_colors) else None
        name = color.capitalize() if color is not None else team.name
        emoji = team_emojis[team_index] if team_index < len(team_emojis) else ""
        lines.append(f"{emoji} *{name} - {score}*")
        team_ids = [str(pid.value) for pid in team.players]
        lines.extend(
            _player_line(pid, player_names, goals, own_goals, assists) for pid in team_ids
        )
    return lines


def _player_line(
    pid: str,
    player_names: dict[str, str],
    goals: dict[str, int],
    own_goals: dict[str, int],
    assists: dict[str, int],
) -> str:
    name = player_names.get(pid, pid)
    stats = "⚽" * goals.get(pid, 0) + "🥅" * own_goals.get(pid, 0) + "🅰️" * assists.get(pid, 0)
    return name + (" " + stats if stats else "")
