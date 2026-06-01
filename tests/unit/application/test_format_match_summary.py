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
"""Tests for FormatMatchSummary use case."""

from datetime import datetime, time

from pyball.application.meetup.format_match_summary import FormatMatchSummary
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.persistence.legacy_stats import LegacyStats


def _pid() -> str:
    """Return a fresh player ID string."""
    return str(PlayerId.generate().value)


class TestFormatMatchSummary:
    """Tests for the FormatMatchSummary use case."""

    def setup_method(self):
        """Set up a finished meetup with two teams and three goal events."""
        # pylint: disable=attribute-defined-outside-init
        self.use_case = FormatMatchSummary()
        self.pid_a1 = _pid()
        self.pid_a2 = _pid()
        self.pid_b1 = _pid()
        self.pid_b2 = _pid()
        self.player_names = {
            self.pid_a1: "Juande",
            self.pid_a2: "Luvo",
            self.pid_b1: "Simón",
            self.pid_b2: "Nacho",
        }
        a1 = PlayerId.from_string(self.pid_a1)
        a2 = PlayerId.from_string(self.pid_a2)
        b1 = PlayerId.from_string(self.pid_b1)
        b2 = PlayerId.from_string(self.pid_b2)
        events = (
            GoalEvent(scorer_id=a1, assistant_id=None, team="A", timestamp=time(20, 5)),
            GoalEvent(scorer_id=b1, assistant_id=a1, team="B", timestamp=time(20, 10)),
            GoalEvent(scorer_id=b1, assistant_id=None, team="B", timestamp=time(20, 15)),
        )
        result = MatchResult(score_a=1, score_b=2, events=events)
        meetup = Meetup.create(date=datetime(2026, 5, 18, 20, 0), location="Parque")
        meetup.set_teams(
            [
                Team.create("A", [a1, a2]),
                Team.create("B", [b1, b2]),
            ]
        )
        meetup.set_result(result)
        self.meetup = meetup
        _ = b2

    def test_header_present(self):
        """Header lines appear at the top of the summary."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "⚽ Día de Partido ⚽" in msg
        assert "🗓 18 Mayo" in msg

    def test_score_in_team_headers(self):
        """Team headers include emoji, capitalized color name and score."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "🟡 *Amarillo - 1*" in msg
        assert "⚫ *Negro - 2*" in msg

    def test_goal_emoji_repeated_per_count(self):
        """A player with two goals gets two goal emojis."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "Simón ⚽⚽" in msg

    def test_assist_emoji_present(self):
        """A player with a goal and an assist gets both emojis."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "Juande ⚽🅰️" in msg

    def test_player_with_no_stats_has_no_emoji(self):
        """A player with no goals or assists appears without any emoji."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "Luvo\n" in msg or msg.endswith("Luvo")

    def test_default_team_names(self):
        """When team_colors/emojis are omitted the defaults blanco/negro are used."""
        msg = self.use_case.execute(self.meetup, self.player_names, date_label="18 Mayo")
        assert "⚪ *Blanco - 1*" in msg
        assert "⚫ *Negro - 2*" in msg


class TestFormatMatchSummaryWithLegacy:
    """FormatMatchSummary overlays assists from LegacyStats when events have none."""

    def setup_method(self):
        """Set up a meetup with goals but no assists in events."""
        # pylint: disable=attribute-defined-outside-init
        self.use_case = FormatMatchSummary()
        self.pid_a1 = _pid()
        self.pid_b1 = _pid()
        self.player_names = {self.pid_a1: "Juande", self.pid_b1: "Simón"}
        a1 = PlayerId.from_string(self.pid_a1)
        b1 = PlayerId.from_string(self.pid_b1)
        events = (GoalEvent(scorer_id=b1, assistant_id=None, team="B", timestamp=time(20, 5)),)
        result = MatchResult(score_a=0, score_b=1, events=events)
        meetup = Meetup.create(date=datetime(2026, 2, 16, 22, 0), location="Parque")
        meetup.set_teams(
            [
                Team.create("A", [a1]),
                Team.create("B", [b1]),
            ]
        )
        meetup.set_result(result)
        self.meetup = meetup

    def test_legacy_assists_appear_when_no_event_assists(self):
        """Legacy assists are shown for players with 0 event assists."""
        legacy_data = {
            "players": {
                self.pid_a1: {"assists_by_match": [{"date": "2026-02-16T22:00:00", "count": 2}]}
            }
        }
        legacy = LegacyStats(legacy_data)
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            date_label="16 Febrero",
            legacy_stats=legacy,
        )
        assert "Juande 🅰️🅰️" in msg

    def test_without_legacy_stats_still_works(self):
        """Passing no legacy_stats (default) does not break the summary."""
        msg = self.use_case.execute(self.meetup, self.player_names, date_label="16 Febrero")
        assert "Juande" in msg
        assert "🅰️" not in msg

    def test_legacy_assists_zero_for_other_dates(self):
        """Legacy assists for a different date are not shown."""
        legacy_data = {
            "players": {
                self.pid_a1: {"assists_by_match": [{"date": "2026-02-23T22:00:00", "count": 3}]}
            }
        }
        legacy = LegacyStats(legacy_data)
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            date_label="16 Febrero",
            legacy_stats=legacy,
        )
        assert "🅰️" not in msg
