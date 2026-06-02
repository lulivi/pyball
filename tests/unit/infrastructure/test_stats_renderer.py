"""Unit tests for StatsHtmlRenderer._build_html and _trend_prefix."""

from datetime import datetime

from pyball.application.meetup.compute_stats import PlayerStats, StatsScopedReport, WinningPair
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer, _trend_prefix


def _make_player(
    player_id: str,
    name: str,
    goals: int,
    assists: int,
    wins: int,
    draws: int,
    losses: int,
    points_rank_delta: int | None = 0,
    goals_rank_delta: int | None = 0,
    assists_rank_delta: int | None = 0,
) -> PlayerStats:
    """Build a PlayerStats for testing."""
    return PlayerStats(
        player_id=player_id,
        player_name=name,
        goals=goals,
        assists=assists,
        own_goals=0,
        matches_played=wins + draws + losses,
        wins=wins,
        draws=draws,
        losses=losses,
        points_rank_delta=points_rank_delta,
        goals_rank_delta=goals_rank_delta,
        assists_rank_delta=assists_rank_delta,
    )


class TestTrendPrefix:
    """Unit tests for the _trend_prefix Jinja2 filter."""

    def test_none_delta_returns_trend_up(self):
        """None delta (new entrant) renders as ▲."""
        result = _trend_prefix(None)
        assert "trend-up" in result
        assert "▲" in result

    def test_positive_delta_returns_trend_up(self):
        """Positive delta (moved up) renders as ▲."""
        result = _trend_prefix(1)
        assert "trend-up" in result

    def test_negative_delta_returns_trend_down(self):
        """Negative delta (dropped) renders as ▼."""
        result = _trend_prefix(-1)
        assert "trend-down" in result
        assert "▼" in result

    def test_zero_delta_returns_trend_same(self):
        """Zero delta (unchanged) renders as ─."""
        result = _trend_prefix(0)
        assert "trend-same" in result
        assert "─" in result

    def test_no_star_symbol(self):
        """★ symbol is never returned."""
        for delta in [None, 0, 1, -1, 5, -5]:
            assert "★" not in _trend_prefix(delta)


class TestBuildHtml:
    """Unit tests for StatsHtmlRenderer._build_html zero-stat filtering."""

    def _build(self, players, chemistry=None, winning_pairs=None) -> str:
        """Build HTML from a player list."""
        scoped = StatsScopedReport(
            players=sorted(players, key=lambda p: p.points, reverse=True),
            chemistry=chemistry or [],
            winning_pairs=winning_pairs or [],
        )
        return StatsHtmlRenderer()._build_html(scoped, "Test")

    def test_player_with_zero_goals_excluded_from_goals_section(self):
        """A player with 0 goals does not appear in the goals bar list."""
        alice = _make_player("a", "Alice", goals=3, assists=1, wins=2, draws=0, losses=1)
        bob = _make_player("b", "Bob", goals=0, assists=2, wins=1, draws=0, losses=2)
        html = self._build([alice, bob])
        goals_col_start = html.index('background:#f72585;"></span> Goles')
        assists_col_start = html.index('background:#3a86ff;"></span> Asistencias')
        goals_section = html[goals_col_start:assists_col_start]
        assert "Bob" not in goals_section

    def test_player_with_zero_assists_excluded_from_assists_section(self):
        """A player with 0 assists does not appear in the assists bar list."""
        alice = _make_player("a", "Alice", goals=3, assists=0, wins=2, draws=0, losses=1)
        bob = _make_player("b", "Bob", goals=1, assists=2, wins=1, draws=0, losses=2)
        html = self._build([alice, bob])
        assists_col_start = html.index('background:#3a86ff;"></span> Asistencias')
        dupla_start = html.index("Conexión Letal")
        assists_section = html[assists_col_start:dupla_start]
        assert "Alice" not in assists_section

    def test_player_with_zero_points_excluded_from_classification(self):
        """A player with 0 points does not appear in the classification table."""
        alice = _make_player("a", "Alice", goals=1, assists=0, wins=0, draws=0, losses=3)
        bob = _make_player("b", "Bob", goals=2, assists=1, wins=2, draws=0, losses=1)
        html = self._build([alice, bob])
        clasificacion_start = html.index("Clasificación</div>")
        split_cols_start = html.index('class="split-cols"')
        classification_section = html[clasificacion_start:split_cols_start]
        assert "Alice" not in classification_section

    def test_player_with_goals_appears_in_goals_section(self):
        """A player with goals appears in the goals section."""
        alice = _make_player("a", "Alice", goals=5, assists=2, wins=3, draws=0, losses=0)
        html = self._build([alice])
        goals_col_start = html.index('background:#f72585;"></span> Goles')
        assists_col_start = html.index('background:#3a86ff;"></span> Asistencias')
        goals_section = html[goals_col_start:assists_col_start]
        assert "Alice" in goals_section

    def test_winning_pair_appears_in_duo_ganador_section(self):
        """A winning pair appears in the Dúo Ganador section."""
        alice = _make_player("a", "Alice", goals=1, assists=0, wins=2, draws=0, losses=0)
        wp = WinningPair(player_a_name="Alice", player_b_name="Bob", count=3)
        html = self._build([alice], winning_pairs=[wp])
        duo_start = html.index("Garantía de Victoria")
        assert "Alice" in html[duo_start:]
        assert "Bob" in html[duo_start:]


class TestBuildHtmlLatestMatchDate:
    """Tests for the latest_match_date subtitle in _build_html."""

    def _make_scoped(self) -> StatsScopedReport:
        """Return a minimal StatsScopedReport for template rendering."""
        player = _make_player("a", "Alice", goals=1, assists=0, wins=1, draws=0, losses=0)
        return StatsScopedReport(players=[player], chemistry=[], winning_pairs=[])

    def test_date_appears_in_html_when_provided(self):
        """When latest_match_date is provided, the formatted date appears in the HTML."""
        scoped = self._make_scoped()
        match_date = datetime(2026, 5, 14, 20, 30)
        html = StatsHtmlRenderer()._build_html(scoped, "Esta temporada", match_date)
        assert "14/05/2026 20:30" in html

    def test_subtitle_absent_when_date_is_none(self):
        """When latest_match_date is None, no subtitle element is rendered."""
        scoped = self._make_scoped()
        html = StatsHtmlRenderer()._build_html(scoped, "Esta temporada", None)
        assert '<p class="card-subtitle">' not in html
