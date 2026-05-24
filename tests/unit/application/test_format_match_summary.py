"""Tests for FormatMatchSummary use case."""

from datetime import datetime, time

from pyball.application.meetup.format_match_summary import FormatMatchSummary
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId


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
        # Juande (a1) scores and later assists; Simón (b1) scores twice
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
        # suppress unused-variable warnings — b2 is used only in player_names
        _ = b2

    def test_header_present(self):
        """Header lines appear at the top of the summary."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_display_names=("AMARILLOS", "NEGROS"),
            date_label="18 Mayo",
        )
        assert "⚽ Día de Partido ⚽" in msg
        assert "🗓 18 Mayo" in msg

    def test_score_in_team_headers(self):
        """Team headers include display name and score."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_display_names=("AMARILLOS", "NEGROS"),
            date_label="18 Mayo",
        )
        assert "*AMARILLOS - 1*" in msg
        assert "*NEGROS - 2*" in msg

    def test_goal_emoji_repeated_per_count(self):
        """A player with two goals gets two goal emojis."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_display_names=("AMARILLOS", "NEGROS"),
            date_label="18 Mayo",
        )
        assert "Simón⚽⚽" in msg

    def test_assist_emoji_present(self):
        """A player with a goal and an assist gets both emojis."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_display_names=("AMARILLOS", "NEGROS"),
            date_label="18 Mayo",
        )
        assert "Juande⚽🅰️" in msg

    def test_player_with_no_stats_has_no_emoji(self):
        """A player with no goals or assists appears without any emoji."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_display_names=("AMARILLOS", "NEGROS"),
            date_label="18 Mayo",
        )
        assert "Luvo\n" in msg or msg.endswith("Luvo")

    def test_default_team_names(self):
        """When team_display_names is omitted the team IDs are used as names."""
        msg = self.use_case.execute(self.meetup, self.player_names, date_label="18 Mayo")
        assert "*A - 1*" in msg
        assert "*B - 2*" in msg
