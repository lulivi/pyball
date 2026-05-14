"""Integration tests for StatsHtmlRenderer (requires WeasyPrint + pymupdf)."""

from datetime import datetime

import pytest

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    PlayerStats,
    StatsReport,
    StatsScopedReport,
    WinningPair,
)
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer


def _make_empty_report() -> StatsReport:
    """Return a StatsReport with no players, chemistry, or winning pairs."""
    empty = StatsScopedReport(players=[], chemistry=[], winning_pairs=[])
    return StatsReport(season=empty, all_time=empty)


def _make_full_report() -> StatsReport:
    """Return a StatsReport with 3 players, 2 chemistry pairs, and 1 winning pair."""
    players = [
        PlayerStats(
            player_id=f"id-{i}",
            player_name=f"Player{i}",
            goals=3 - i,
            assists=3 - i,
            matches_played=10,
            wins=3 - i,
            draws=1,
            losses=i,
            points_rank_delta=0,
            goals_rank_delta=0,
            assists_rank_delta=0,
        )
        for i in range(3)
    ]
    chemistry = [
        ChemistryPair(scorer_name="Player0", assistant_name="Player1", count=3),
        ChemistryPair(scorer_name="Player1", assistant_name="Player2", count=1),
    ]
    winning_pairs = [WinningPair(player_a_name="Player0", player_b_name="Player1", count=5)]
    scoped = StatsScopedReport(players=players, chemistry=chemistry, winning_pairs=winning_pairs)
    return StatsReport(season=scoped, all_time=scoped)


class TestStatsHtmlRenderer:
    """Integration tests for StatsHtmlRenderer.render()."""

    @pytest.mark.asyncio
    async def test_render_season_returns_bytes(self):
        """render(scope='season') returns non-empty bytes."""
        report = _make_full_report()
        png = await StatsHtmlRenderer().render(report, scope="season")
        assert isinstance(png, bytes) and len(png) > 0

    @pytest.mark.asyncio
    async def test_render_alltime_returns_bytes(self):
        """render(scope='alltime') returns non-empty bytes."""
        report = _make_full_report()
        png = await StatsHtmlRenderer().render(report, scope="alltime")
        assert isinstance(png, bytes) and len(png) > 0

    @pytest.mark.asyncio
    async def test_render_produces_valid_png(self):
        """render() output starts with the PNG magic bytes."""
        report = _make_full_report()
        png = await StatsHtmlRenderer().render(report, scope="season")
        assert png[:4] == b"\x89PNG"

    @pytest.mark.asyncio
    async def test_render_empty_report_does_not_raise(self):
        """render() handles an empty report without raising."""
        report = _make_empty_report()
        png = await StatsHtmlRenderer().render(report, scope="season")
        assert isinstance(png, bytes) and len(png) > 0

    @pytest.mark.asyncio
    async def test_season_and_alltime_produce_different_images_when_data_differs(self):
        """season and alltime scopes produce different PNG bytes when data differs."""
        players_season = [
            PlayerStats(
                player_id="id-0",
                player_name="Alice",
                goals=3,
                assists=1,
                matches_played=5,
                wins=3,
                draws=0,
                losses=2,
                points_rank_delta=None,
                goals_rank_delta=None,
                assists_rank_delta=None,
            )
        ]
        players_all = [
            PlayerStats(
                player_id="id-0",
                player_name="Alice",
                goals=10,
                assists=5,
                matches_played=20,
                wins=12,
                draws=2,
                losses=6,
                points_rank_delta=0,
                goals_rank_delta=0,
                assists_rank_delta=0,
            )
        ]
        report = StatsReport(
            season=StatsScopedReport(players=players_season, chemistry=[], winning_pairs=[]),
            all_time=StatsScopedReport(players=players_all, chemistry=[], winning_pairs=[]),
        )
        season_png = await StatsHtmlRenderer().render(report, scope="season")
        alltime_png = await StatsHtmlRenderer().render(report, scope="alltime")
        assert season_png != alltime_png

    def test_no_star_symbol_in_html(self):
        """The ★ indicator is never shown regardless of player data."""
        report = _make_full_report()
        scoped = report.season
        # pylint: disable=protected-access
        html = StatsHtmlRenderer()._build_html(scoped, "Test")
        assert "★" not in html

    @pytest.mark.asyncio
    async def test_render_with_latest_match_date_returns_bytes(self):
        """render() with a non-None latest_match_date produces valid PNG bytes."""
        report = _make_full_report()
        report.latest_match_date = datetime(2026, 5, 14, 20, 30)
        png = await StatsHtmlRenderer().render(report, scope="season")
        assert png[:4] == b"\x89PNG"
