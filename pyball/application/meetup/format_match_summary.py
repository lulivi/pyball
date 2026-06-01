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

from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.persistence.legacy_stats import LegacyStats


class FormatMatchSummary:
    """Build the WhatsApp-format post-match summary for a finished meetup."""

    def execute(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        meetup: Meetup,
        player_names: dict[str, str],
        team_colors: tuple[str, str] = ("blanco", "negro"),
        team_emojis: tuple[str, str] = ("⚪", "⚫"),
        date_label: str | None = None,
        legacy_stats: LegacyStats | None = None,
    ) -> str:
        """Return the WhatsApp-ready summary string.

        Args:
            meetup: A finished meetup with result and teams.
            player_names: Mapping of str(player_id.value) to display name.
            team_colors: Color name for team A and team B (capitalized as display name).
            team_emojis: Circle emoji for team A and team B.
            date_label: Pre-formatted date string (e.g. "18 Mayo"). If None,
                derived from meetup.date using the current locale.
            legacy_stats: Optional legacy statistics. When provided, assists for
                players with no event assists are read from it for this match date.

        Returns:
            Multi-line WhatsApp message string.
        """
        if meetup.result is None:
            raise ValueError("Meetup has no result yet")
        if meetup.teams is None:
            raise ValueError("Meetup has no teams yet")

        result = meetup.result
        teams = meetup.teams
        name_a = team_colors[0].capitalize()
        name_b = team_colors[1].capitalize()
        emoji_a = team_emojis[0]
        emoji_b = team_emojis[1]
        label = date_label or meetup.date.strftime("%-d %B").title()

        goals: dict[str, int] = {}
        assists: dict[str, int] = {}
        for event in result.events:
            sid = str(event.scorer_id.value)
            goals[sid] = goals.get(sid, 0) + 1
            if event.assistant_id:
                aid = str(event.assistant_id.value)
                assists[aid] = assists.get(aid, 0) + 1

        if legacy_stats is not None:
            all_pids = [str(pid.value) for team in teams for pid in team.players]
            for pid in all_pids:
                if assists.get(pid, 0) == 0:
                    legacy_count = legacy_stats.get_assists_for_match(pid, meetup.date)
                    if legacy_count:
                        assists[pid] = legacy_count

        team_a_ids = [str(pid.value) for pid in teams[0].players]
        team_b_ids = [str(pid.value) for pid in teams[1].players]

        lines = [
            "⚽ Día de Partido ⚽",
            f"🗓 {label}",
            "",
            "*RESULTADO:*",
            "",
            f"{emoji_a} *{name_a} - {result.score_a}*",
            *[_player_line(pid, player_names, goals, assists) for pid in team_a_ids],
            "",
            f"{emoji_b} *{name_b} - {result.score_b}*",
            *[_player_line(pid, player_names, goals, assists) for pid in team_b_ids],
        ]
        return "\n".join(lines)


def _player_line(
    pid: str,
    player_names: dict[str, str],
    goals: dict[str, int],
    assists: dict[str, int],
) -> str:
    name = player_names.get(pid, pid)
    stats = "⚽" * goals.get(pid, 0) + "🅰️" * assists.get(pid, 0)
    return name + (" " + stats if stats else "")
