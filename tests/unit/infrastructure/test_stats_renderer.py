"""Unit tests for StatsHtmlRenderer._build_html and _trend_prefix."""

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
        # The goals mini-title uses a red dot; use it as an anchor to find the goals column
        goals_col_start = html.index('background:#e74c3c;"></span>Goles')
        assists_col_start = html.index('background:#3498db;"></span>Asistencias')
        goals_section = html[goals_col_start:assists_col_start]
        assert "Bob" not in goals_section

    def test_player_with_zero_assists_excluded_from_assists_section(self):
        """A player with 0 assists does not appear in the assists bar list."""
        alice = _make_player("a", "Alice", goals=3, assists=0, wins=2, draws=0, losses=1)
        bob = _make_player("b", "Bob", goals=1, assists=2, wins=1, draws=0, losses=2)
        html = self._build([alice, bob])
        # The assists mini-title uses a blue dot; use it as an anchor to find the assists column
        assists_col_start = html.index('background:#3498db;"></span>Asistencias')
        parejas_start = html.index("Parejas")
        assists_section = html[assists_col_start:parejas_start]
        assert "Alice" not in assists_section

    def test_player_with_zero_points_excluded_from_classification(self):
        """A player with 0 points does not appear in the classification table."""
        alice = _make_player("a", "Alice", goals=1, assists=0, wins=0, draws=0, losses=3)
        bob = _make_player("b", "Bob", goals=2, assists=1, wins=2, draws=0, losses=1)
        html = self._build([alice, bob])
        # The classification section title uses a trophy emoji
        clasificacion_start = html.index("Clasificación</div>")
        # The goals+assists section starts with a distinctive comment
        goles_asistencias_start = html.index("Goles y Asistencias")
        classification_section = html[clasificacion_start:goles_asistencias_start]
        assert "Alice" not in classification_section

    def test_player_with_goals_appears_in_goals_section(self):
        """A player with goals appears in the goals section."""
        alice = _make_player("a", "Alice", goals=5, assists=2, wins=3, draws=0, losses=0)
        html = self._build([alice])
        goals_col_start = html.index('background:#e74c3c;"></span>Goles')
        assists_col_start = html.index('background:#3498db;"></span>Asistencias')
        goals_section = html[goals_col_start:assists_col_start]
        assert "Alice" in goals_section
