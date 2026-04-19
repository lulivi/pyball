"""Integration tests for StatsHtmlRenderer (requires WeasyPrint + pymupdf)."""

import pytest

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    PlayerStats,
    StatsReport,
    StatsScopedReport,
)
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer


def _make_empty_report() -> StatsReport:
    """Return a StatsReport with no players or chemistry."""
    empty = StatsScopedReport(players=[], chemistry=[])
    return StatsReport(season=empty, all_time=empty)


def _make_full_report() -> StatsReport:
    """Return a StatsReport with 3 players and 2 chemistry pairs."""
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
    scoped = StatsScopedReport(players=players, chemistry=chemistry)
    return StatsReport(season=scoped, all_time=scoped)


class TestStatsHtmlRenderer:
    """Integration tests for StatsHtmlRenderer.render()."""

    @pytest.mark.asyncio
    async def test_render_returns_two_bytes_objects(self):
        """render() returns a tuple of two non-empty bytes objects."""
        report = _make_full_report()
        season_png, alltime_png = await StatsHtmlRenderer().render(report)
        assert isinstance(season_png, bytes) and len(season_png) > 0
        assert isinstance(alltime_png, bytes) and len(alltime_png) > 0

    @pytest.mark.asyncio
    async def test_render_produces_valid_png(self):
        """render() output starts with the PNG magic bytes."""
        report = _make_full_report()
        season_png, alltime_png = await StatsHtmlRenderer().render(report)
        png_magic = b"\x89PNG"
        assert season_png[:4] == png_magic
        assert alltime_png[:4] == png_magic

    @pytest.mark.asyncio
    async def test_render_empty_report_does_not_raise(self):
        """render() handles an empty report without raising."""
        report = _make_empty_report()
        season_png, alltime_png = await StatsHtmlRenderer().render(report)
        assert isinstance(season_png, bytes) and len(season_png) > 0
        assert isinstance(alltime_png, bytes) and len(alltime_png) > 0

    @pytest.mark.asyncio
    async def test_season_and_alltime_images_differ(self):
        """season and all_time images are different bytes when data differs."""
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
            season=StatsScopedReport(players=players_season, chemistry=[]),
            all_time=StatsScopedReport(players=players_all, chemistry=[]),
        )
        season_png, alltime_png = await StatsHtmlRenderer().render(report)
        assert season_png != alltime_png

    def test_no_star_symbol_in_html(self):
        """The ★ indicator is never shown regardless of player data."""
        report = _make_full_report()
        scoped = report.season
        # pylint: disable=protected-access
        html = StatsHtmlRenderer()._build_html(scoped, "Test")
        assert "★" not in html
