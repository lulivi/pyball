"""Statistics image renderer using WeasyPrint and a Jinja2 HTML template."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import fitz
import jinja2
import weasyprint
from markupsafe import Markup

from pyball.application.meetup.compute_stats import StatsReport, StatsScopedReport

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "stats_template.html.jinja"

_BG_COLOR_HEX = "#0f0f1a"
_BG_COLOR_BYTES = bytes(int(_BG_COLOR_HEX[i : i + 2], 16) for i in (1, 3, 5))


def _trend_prefix(delta: int | None) -> Markup:
    """Return an HTML span with the trend symbol for the given delta.

    Args:
        delta: Rank position change (positive=up, negative=down, None=new entrant).

    Returns:
        Safe HTML Markup with the trend span.
    """
    if delta is None or delta > 0:
        return Markup('<span class="trend-up">▲</span>')
    if delta < 0:
        return Markup('<span class="trend-down">▼</span>')
    return Markup('<span class="trend-same">─</span>')


def _build_jinja_env() -> jinja2.Environment:
    """Build and return the Jinja2 environment with the trend_prefix filter registered.

    Returns:
        Configured Jinja2 Environment.
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATE_DIR),
        autoescape=True,
    )
    env.filters["trend_prefix"] = _trend_prefix
    return env


_JINJA_ENV = _build_jinja_env()


class StatsHtmlRenderer:
    """Renders a StatsReport into a PNG image for the requested scope via WeasyPrint."""

    async def render(self, report: StatsReport, scope: str = "season") -> bytes:
        """Generate a PNG image for the requested scope.

        Args:
            report: Fully computed StatsReport.
            scope: Either "season" or "alltime".

        Returns:
            Raw PNG bytes for the requested scope.
        """
        if scope == "alltime":
            return await self._render_scope(report.all_time, "Histórico")
        if scope != "season":
            logger.warning("Unknown scope %r passed to render(); defaulting to 'season'", scope)
        return await self._render_scope(report.season, "Esta temporada")

    async def _render_scope(self, scoped: StatsScopedReport, title: str) -> bytes:
        """Render a single scope into PNG bytes.

        Args:
            scoped: Scope-specific stats (players, chemistry, winning pairs).
            title: Section title shown at the top of the image.

        Returns:
            Raw PNG bytes.
        """
        html = self._build_html(scoped, title)
        return await asyncio.to_thread(self._screenshot, html)

    def _build_html(self, scoped: StatsScopedReport, title: str) -> str:
        """Render the Jinja2 template with the given scope data.

        Args:
            scoped: Scope-specific stats (players, chemistry, winning pairs).
            title: Section title shown at the top of the image.

        Returns:
            Rendered HTML string ready for WeasyPrint.
        """
        players = [p for p in scoped.players if p.points > 0][:10]
        players_by_goals = sorted(
            [p for p in scoped.players if p.goals > 0],
            key=lambda p: (-p.goals, p.player_name),
        )[:10]
        players_by_assists = sorted(
            [p for p in scoped.players if p.assists > 0],
            key=lambda p: (-p.assists, p.player_name),
        )[:10]
        chemistry = scoped.chemistry[:5]
        winning_pairs = scoped.winning_pairs[:5]

        max_goals = max((p.goals for p in players_by_goals), default=0) or 1
        max_assists = max((p.assists for p in players_by_assists), default=0) or 1
        max_chemistry = max((c.count for c in chemistry), default=0) or 1
        max_winning = max((wp.count for wp in winning_pairs), default=0) or 1

        template = _JINJA_ENV.get_template(_TEMPLATE_NAME)
        return template.render(
            title=title,
            bg_color=_BG_COLOR_HEX,
            players=players,
            players_by_goals=players_by_goals,
            players_by_assists=players_by_assists,
            chemistry=chemistry,
            winning_pairs=winning_pairs,
            max_goals=max_goals,
            max_assists=max_assists,
            max_chemistry=max_chemistry,
            max_winning=max_winning,
        )

    def _screenshot(self, html: str) -> bytes:
        """Render HTML to PNG bytes via WeasyPrint (PDF) and pymupdf.

        Args:
            html: Fully rendered HTML string.

        Returns:
            Raw PNG bytes, cropped to content height.
        """
        pdf = weasyprint.HTML(string=html).write_pdf()
        doc = fitz.open(stream=pdf, filetype="pdf")
        mat = fitz.Matrix(4, 4)
        pixmaps = [page.get_pixmap(matrix=mat) for page in doc]

        if len(pixmaps) == 1:
            full = pixmaps[0]
        else:
            total_h = sum(p.height for p in pixmaps)
            w = pixmaps[0].width
            all_samples = b"".join(bytes(p.samples) for p in pixmaps)
            full = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, total_h), all_samples)

        return self._crop_whitespace(full).tobytes("png")

    def _crop_whitespace(self, pix: fitz.Pixmap) -> fitz.Pixmap:
        """Return a new Pixmap with trailing background rows removed."""
        w, h = pix.width, pix.height
        samples = bytes(pix.samples)
        n = pix.n

        # EL CAMBIO CLAVE: Tomamos la última fila COMPLETA como referencia matemática.
        # Si hay distorsiones en los bordes debido al escalado x3, esta fila
        # ya las contiene, haciendo que la comparación sea perfectamente simétrica.
        start_last_row = (h - 1) * w * n
        reference_row = samples[start_last_row:]

        last_row = h - 1
        for row in range(h - 1, -1, -1):
            start = row * w * n
            end = start + (w * n)

            # Comparamos la fila actual contra nuestra fila de referencia
            if samples[start:end] != reference_row:
                last_row = row
                break

        # Mantengo 40px de padding porque al escalar x3, los píxeles son más pequeños
        crop_h = min(last_row + 80, h)

        if crop_h >= h:
            return pix

        result = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, crop_h), False)
        result.copy(pix, fitz.IRect(0, 0, w, crop_h))
        return result
