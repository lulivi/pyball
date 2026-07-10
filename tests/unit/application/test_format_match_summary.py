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
from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, Team
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
        team_a = Team.create("A", [a1, a2])
        team_b = Team.create("B", [b1, b2])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=result))
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
        assert msg.startswith("🎉 *Partido terminado:* 18 Mayo\n📍 *Lugar:* Parque")

    def test_header_uses_iso_date_and_time_by_default(self):
        """Without an explicit date_label, the header shows "YYYY-MM-DD HH:MM"."""
        msg = self.use_case.execute(self.meetup, self.player_names)
        assert "🎉 *Partido terminado:* 2026-05-18 20:00" in msg

    def test_header_omits_location_line_when_meetup_has_none(self):
        """A meetup with no location has no "📍 Lugar:" line."""
        meetup = Meetup.create(date=datetime(2026, 5, 18, 20, 0), location="Parque")
        a1 = PlayerId.from_string(self.pid_a1)
        b1 = PlayerId.from_string(self.pid_b1)
        team_a, team_b = Team.create("A", [a1]), Team.create("B", [b1])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, ())))
        meetup.location = ""
        msg = self.use_case.execute(meetup, self.player_names, date_label="18 Mayo")
        assert "📍" not in msg

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

    def test_single_match_has_no_round_separator(self):
        """A classic (single-match) summary has no round-separator line."""
        msg = self.use_case.execute(self.meetup, self.player_names, date_label="18 Mayo")
        assert "➖" not in msg

    def test_classic_summary_has_goles_section_in_chronological_order(self):
        """A classic match's summary lists every event, in order, under *GOLES:*."""
        msg = self.use_case.execute(
            self.meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )
        assert "*GOLES:*" in msg
        goles_section = msg.split("*GOLES:*", 1)[1]
        lines = [line for line in goles_section.splitlines() if line.strip()]
        assert lines == [
            "  - ⚽ 05' Juande",
            "  - ⚽ 10' Simón (asist. Juande)",
            "  - ⚽ 15' Simón",
        ]

    def test_classic_summary_no_goles_section_without_events(self):
        """A match with a score but no recorded events has no *GOLES:* section."""
        meetup = Meetup.create(date=datetime(2026, 5, 18, 20, 0), location="Parque")
        a1 = PlayerId.from_string(self.pid_a1)
        b1 = PlayerId.from_string(self.pid_b1)
        team_a = Team.create("A", [a1])
        team_b = Team.create("B", [b1])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, ())))

        msg = self.use_case.execute(meetup, self.player_names, date_label="18 Mayo")
        assert "*GOLES:*" not in msg

    def test_own_goal_shown_with_net_emoji_on_scorer_line(self):
        """An own-goal event shows 🥅 on the scorer's line; no goal on the benefiting team."""
        a1 = PlayerId.from_string(self.pid_a1)
        b1 = PlayerId.from_string(self.pid_b1)

        own_goal_event = GoalEvent(
            scorer_id=a1,
            assistant_id=None,
            team="B",
            timestamp=time(20, 20),
            is_own_goal=True,
        )
        result = MatchResult(score_a=0, score_b=1, events=(own_goal_event,))
        meetup = Meetup.create(date=datetime(2026, 5, 18, 20, 0), location="Parque")
        team_a = Team.create("A", [a1, PlayerId.from_string(self.pid_a2)])
        team_b = Team.create("B", [b1, PlayerId.from_string(self.pid_b2)])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=result))

        msg = self.use_case.execute(
            meetup,
            self.player_names,
            team_colors=("amarillo", "negro"),
            team_emojis=("🟡", "⚫"),
            date_label="18 Mayo",
        )

        lines = msg.splitlines()
        juande_line = next(line for line in lines if "Juande" in line)
        assert "🥅" in juande_line
        assert "⚽" not in juande_line
        # No goal icon on Simón's line (he did not score)
        simon_line = next(line for line in lines if "Simón" in line)
        assert "⚽" not in simon_line
        assert "🥅" not in simon_line

        assert "  - 🥅 20' Juande (en propia)" in msg


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
        team_a = Team.create("A", [a1])
        team_b = Team.create("B", [b1])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=result))
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


def test_triangular_summary_lists_every_round():
    """A 3-team meetup's summary shows one score line per round played."""
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
    meetup.add_match(Match(teams_playing=(team_a, team_c), result=MatchResult(1, 1, ())))
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa", str(p3.value): "Nico"}
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    assert "Blanco - 2" in summary
    assert "Negro - 0" in summary
    assert "Blanco - 1" in summary
    assert "Rojo - 1" in summary


def test_triangular_round_blocks_have_header_and_events_only():
    """A triangular round shows only the two score headers plus that round's events

    -- no per-player roster lines, since full rosters (with aggregate stats)
    already appear once in the "*EQUIPOS:*" section at the top.
    """
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    scorer, quiet, keeper = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    opponent = PlayerId.generate()
    team_a = Team.create("A", [scorer, quiet, keeper])
    team_b = Team.create("B", [opponent])
    team_c = Team.create("C", [PlayerId.generate()])
    meetup.teams = [team_a, team_b, team_c]

    events = (GoalEvent(scorer_id=scorer, assistant_id=None, team="A", timestamp=time(20, 5)),)
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, events)))
    meetup.close()

    player_names = {
        str(scorer.value): "Marca",
        str(quiet.value): "Callado",
        str(keeper.value): "Portero",
        str(opponent.value): "Rival",
    }
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    resultado_section = summary.split("*RESULTADO:*", 1)[1]
    assert "  - ⚽ 05' Marca" in resultado_section
    assert "Callado" not in resultado_section
    assert "Portero" not in resultado_section
    assert "Rival" not in resultado_section

    # But the full roster still appears once, in the standings section.
    equipos_section = summary.split("*EQUIPOS:*", 1)[1].split("*RESULTADO:*", 1)[0]
    assert "Callado" in equipos_section
    assert "Portero" in equipos_section


def test_triangular_round_block_has_no_events_line_when_scoreless():
    """A 0-0 triangular round shows only the two score headers, no events list."""
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(0, 0, ())))
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa", str(p3.value): "Nico"}
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    resultado_section = summary.split("*RESULTADO:*", 1)[1]
    assert "-" not in resultado_section.split("Negro - 0*", 1)[1]


def test_triangular_standings_show_per_player_aggregate_stats():
    """The EQUIPOS section shows each player's session-wide goal/assist stats."""
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    events = (GoalEvent(scorer_id=p1, assistant_id=None, team="A", timestamp=time(20, 5)),)
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, events)))
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa", str(p3.value): "Nico"}
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    equipos_section = summary.split("*EQUIPOS:*", 1)[1].split("*RESULTADO:*", 1)[0]
    assert "Dani ⚽" in equipos_section
    assert "Rafa\n" in equipos_section or equipos_section.rstrip().endswith("Rafa")


def test_triangular_summary_has_team_standings_section():
    """A 3-team summary opens with each team's roster and win/draw/loss record."""
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
    meetup.add_match(Match(teams_playing=(team_a, team_c), result=MatchResult(1, 1, ())))
    meetup.add_match(Match(teams_playing=(team_c, team_b), result=MatchResult(2, 1, ())))
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa", str(p3.value): "Nico"}
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    lines = summary.splitlines()
    assert "*EQUIPOS:*" in lines
    # Team A: win vs B, draw vs C -> 1V 1E 0D. Roster line follows the header.
    idx_a = next(i for i, line in enumerate(lines) if "Blanco" in line and "V" in line)
    assert lines[idx_a] == "⚪ *Blanco* (1V 1E 0D)"
    assert lines[idx_a + 1] == "Dani"
    # Team B: loss vs A, loss vs C -> 0V 0E 2D.
    idx_b = next(i for i, line in enumerate(lines) if "Negro" in line and "V" in line)
    assert lines[idx_b] == "⚫ *Negro* (0V 0E 2D)"
    assert lines[idx_b + 1] == "Rafa"
    # Team C: draw vs A, win vs B -> 1V 1E 0D.
    idx_c = next(i for i, line in enumerate(lines) if "Rojo" in line and "V" in line)
    assert lines[idx_c] == "🔴 *Rojo* (1V 1E 0D)"
    assert lines[idx_c + 1] == "Nico"
    # The standings section comes before the round-by-round breakdown.
    assert summary.index("*EQUIPOS:*") < summary.index("*RESULTADO:*")


class TestFormatMatchSummaryNoStandings:
    """A classic (2-team) summary has no team-standings section."""

    def test_no_standings_section_for_classic_meetup(self):
        """The classic 2-team path never shows the "*EQUIPOS:*" standings section."""
        meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        meetup.teams = [team_a, team_b]
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, ())))
        meetup.close()

        player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
        summary = FormatMatchSummary().execute(meetup, player_names, date_label="18 Mayo")

        assert "*EQUIPOS:*" not in summary


def test_triangular_summary_has_separator_between_rounds():
    """Consecutive rounds are visually separated by a divider line."""
    meetup = Meetup.create(datetime(2026, 5, 18, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.teams = [team_a, team_b, team_c]
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
    meetup.add_match(Match(teams_playing=(team_a, team_c), result=MatchResult(1, 1, ())))
    meetup.add_match(Match(teams_playing=(team_c, team_b), result=MatchResult(2, 1, ())))
    meetup.close()

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa", str(p3.value): "Nico"}
    summary = FormatMatchSummary().execute(
        meetup,
        player_names,
        team_colors=("blanco", "negro", "rojo"),
        team_emojis=("⚪", "⚫", "🔴"),
    )

    # 3 rounds played -> exactly 2 separators, one between each consecutive pair.
    assert summary.count("➖➖➖➖➖➖➖➖➖➖") == 2
    # No separator before the very first round's header.
    assert not summary.split("*RESULTADO:*", 1)[1].lstrip("\n").startswith("➖")
