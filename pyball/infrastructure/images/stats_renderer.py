"""Statistics image renderer using Playwright and a Jinja2 HTML template."""

from __future__ import annotations

from pathlib import Path

import jinja2

from markupsafe import Markup
from playwright.async_api import async_playwright

from pyball.application.meetup.compute_stats import PlayerStats, StatsReport, StatsScopedReport

_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "stats_template.html"


def _trend_prefix(player: PlayerStats) -> Markup:
    """Return an HTML span with the trend symbol for the given player.

    Args:
        player: PlayerStats with rank_delta set.

    Returns:
        Safe HTML Markup with the trend span.
    """
    delta = player.rank_delta
    if delta is None:
        return Markup('<span class="trend-new">★</span>')
    if delta > 0:
        return Markup('<span class="trend-up">▲</span>')
    if delta < 0:
        return Markup('<span class="trend-down">▼</span>')
    return Markup('<span class="trend-same">─</span>')


class StatsHtmlRenderer:
    """Renders a StatsReport into two PNG images (season and all-time) via Playwright."""

    async def render(self, report: StatsReport) -> tuple[bytes, bytes]:
        """Generate PNG images for season and all-time scopes.

        Args:
            report: Fully computed StatsReport.

        Returns:
            Tuple of (season_png, all_time_png) as raw bytes.
        """
        season_png = await self._render_scope(report.season, "Esta temporada")
        all_time_png = await self._render_scope(report.all_time, "Histórico")
        return season_png, all_time_png

    async def _render_scope(self, scoped: StatsScopedReport, title: str) -> bytes:
        """Render a single scope into PNG bytes.

        Args:
            scoped: Scope-specific stats (players + chemistry).
            title: Section title shown at the top of the image.

        Returns:
            Raw PNG bytes.
        """
        html = self._build_html(scoped, title)
        return await self._screenshot(html)

    def _build_html(self, scoped: StatsScopedReport, title: str) -> str:
        """Render the Jinja2 template with the given scope data.

        Args:
            scoped: Scope-specific stats (players + chemistry).
            title: Section title shown at the top of the image.

        Returns:
            Rendered HTML string ready for Playwright.
        """
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=True,
        )
        env.filters["trend_prefix"] = _trend_prefix

        players = scoped.players[:10]
        players_by_goals = sorted(scoped.players, key=lambda p: p.goals, reverse=True)[:10]
        players_by_assists = sorted(scoped.players, key=lambda p: p.assists, reverse=True)[:10]
        chemistry = scoped.chemistry[:5]

        max_goals = max((p.goals for p in players_by_goals), default=0) or 1
        max_assists = max((p.assists for p in players_by_assists), default=0) or 1
        max_chemistry = max((c.count for c in chemistry), default=0) or 1

        template = env.get_template(_TEMPLATE_NAME)
        return template.render(
            title=title,
            players=players,
            players_by_goals=players_by_goals,
            players_by_assists=players_by_assists,
            chemistry=chemistry,
            max_goals=max_goals,
            max_assists=max_assists,
            max_chemistry=max_chemistry,
        )

    async def _screenshot(self, html: str) -> bytes:
        """Launch Chromium, render the HTML, and return a full-page PNG.

        Args:
            html: Fully rendered HTML string.

        Returns:
            Raw PNG bytes of the full page screenshot.
        """
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
            )
            await page.set_content(html, wait_until="load")
            png = await page.screenshot(full_page=True)
            await browser.close()
            return png
