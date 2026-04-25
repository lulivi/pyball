# HTML Stats Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the matplotlib-based `StatsImageRenderer` with a `StatsHtmlRenderer` that renders a Jinja2 HTML dark-card template and screenshots it via Playwright's headless Chromium.

**Architecture:** `StatsHtmlRenderer.render()` is async. It calls `_build_html()` (Jinja2 template → HTML string) then `_screenshot()` (Playwright → PNG bytes). The template lives in `pyball/infrastructure/images/stats_template.html`. The only call site is `pyball/infrastructure/http/app.py::_post_match_stats`, which already runs in an async context.

**Tech Stack:** Python 3.12, Jinja2 ≥3.1, Playwright ≥1.44 (Chromium), pytest-asyncio (strict mode).

---

## File Map

| Action | File |
|--------|------|
| Modify | `pyproject.toml` — remove `matplotlib`, add `jinja2` + `playwright` |
| Modify | `pyproject.toml` `[tool.mypy.overrides]` — replace `matplotlib.*` with `playwright.*` |
| Delete | `pyball/infrastructure/images/stats_renderer.py` (old `StatsImageRenderer`) |
| Create | `pyball/infrastructure/images/stats_renderer.py` (new `StatsHtmlRenderer`) |
| Create | `pyball/infrastructure/images/stats_template.html` |
| Modify | `pyball/infrastructure/http/app.py` — import + `await` |
| Modify | `docker/Dockerfile` — `playwright install chromium --with-deps` |
| Delete | `tests/unit/infrastructure/test_stats_renderer.py` |
| Create | `tests/integration/test_stats_renderer.py` |

---

### Task 1: Update dependencies and install

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit pyproject.toml — swap matplotlib for jinja2 + playwright**

In `[tool.poetry.dependencies]` replace:
```toml
matplotlib = ">=3.7"
```
with:
```toml
jinja2 = "^3.1"
playwright = "^1.44"
```

In `[tool.mypy.overrides]` replace:
```toml
module = ["decouple", "event_bus", "matplotlib", "matplotlib.*"]
```
with:
```toml
module = ["decouple", "event_bus", "playwright", "playwright.*"]
```

- [ ] **Step 2: Install new dependencies**

```bash
poetry lock && poetry install --with test
```

Expected: lock file updated, jinja2 and playwright installed, matplotlib removed.

- [ ] **Step 3: Install Playwright's Chromium browser**

```bash
poetry run playwright install chromium
```

Expected: Chromium downloaded to `~/.cache/ms-playwright/` (or equivalent). No error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "deps: replace matplotlib with jinja2 + playwright"
```

---

### Task 2: Write failing integration test

**Files:**
- Delete: `tests/unit/infrastructure/test_stats_renderer.py`
- Create: `tests/integration/test_stats_renderer.py`

- [ ] **Step 1: Delete the old unit test**

```bash
rm tests/unit/infrastructure/test_stats_renderer.py
```

- [ ] **Step 2: Create the new integration test**

Create `tests/integration/test_stats_renderer.py`:

```python
"""Integration tests for StatsHtmlRenderer (requires Playwright + Chromium)."""

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
            goals=5 - i,
            assists=i,
            matches_played=10,
            wins=5 - i,
            draws=1,
            losses=i,
            rank_delta=i - 1,
        )
        for i in range(3)
    ]
    players[2].rank_delta = None  # new entry — ★ symbol
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
                rank_delta=None,
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
                rank_delta=0,
            )
        ]
        report = StatsReport(
            season=StatsScopedReport(players=players_season, chemistry=[]),
            all_time=StatsScopedReport(players=players_all, chemistry=[]),
        )
        season_png, alltime_png = await StatsHtmlRenderer().render(report)
        assert season_png != alltime_png
```

- [ ] **Step 3: Run the test to verify it fails for the right reason**

```bash
poetry run pytest tests/integration/test_stats_renderer.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `StatsHtmlRenderer` does not exist yet. This confirms the test is wired correctly.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_stats_renderer.py tests/unit/infrastructure/
git commit -m "test: add integration tests for StatsHtmlRenderer (TDD)"
```

---

### Task 3: Create the Jinja2 HTML template

**Files:**
- Create: `pyball/infrastructure/images/stats_template.html`

- [ ] **Step 1: Create `stats_template.html`**

Create `pyball/infrastructure/images/stats_template.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=390">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #0f0f1a;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  color: #fff;
}
.card { background: #0f0f1a; padding: 20px; }
.card-title {
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #a0a0c0;
  text-transform: uppercase;
  margin-bottom: 18px;
}
.section { margin-bottom: 16px; }
.section-title {
  font-size: 10px;
  font-weight: 700;
  color: #6c6c9a;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 6px;
}
.section-body {
  background: #1a1a2e;
  border-radius: 6px;
  padding: 8px 10px;
}
/* Clasificación table */
.ranking-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.ranking-table thead td {
  color: #6c6c9a;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 4px 5px 4px;
}
.ranking-table tbody tr { border-top: 1px solid rgba(255,255,255,0.05); }
.ranking-table tbody tr.odd { background: #1f1f38; }
.ranking-table tbody td { padding: 4px; }
.ranking-table .pos { color: #6c6c9a; width: 18px; }
.ranking-table .pos.gold { color: #f0c040; }
.ranking-table .num { text-align: center; color: #c0c0d0; }
.ranking-table .pts { text-align: center; font-weight: 700; }
/* Trend symbols */
.trend-up { color: #2ecc71; }
.trend-down { color: #e74c3c; }
.trend-same { color: #6c6c9a; }
.trend-new { color: #f0c040; }
/* Split columns (goles / asistencias) */
.split-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.mini-title {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.dot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
/* Bar rows */
.bar-row { display: flex; align-items: center; gap: 5px; margin-bottom: 4px; }
.bar-row:last-child { margin-bottom: 0; }
.bar-name {
  font-size: 10px;
  color: #d0d0e0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 80px;
}
.bar-track { flex: 1; }
.bar { height: 7px; border-radius: 3px; min-width: 3px; }
.bar.goals { background: #e74c3c; }
.bar.assists { background: #3498db; }
.bar.chemistry { background: #2ecc71; }
.bar-value { font-size: 9px; color: #6c6c9a; white-space: nowrap; }
/* Wide bar rows (parejas) */
.bar-row-wide { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.bar-row-wide:last-child { margin-bottom: 0; }
.bar-name-wide { font-size: 11px; color: #d0d0e0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 160px; }
</style>
</head>
<body>
<div class="card">
  <div class="card-title">{{ title }}</div>

  <!-- Clasificación -->
  <div class="section">
    <div class="section-title">🏆 Clasificación</div>
    <div class="section-body">
      <table class="ranking-table">
        <thead>
          <tr>
            <td class="pos">#</td>
            <td>Jugador</td>
            <td class="num">PJ</td>
            <td class="num">G</td>
            <td class="num">E</td>
            <td class="num">P</td>
            <td class="num" style="color:#f0c040;">Pts</td>
          </tr>
        </thead>
        <tbody>
          {% for p in players %}
          <tr{% if loop.index is odd %} class="odd"{% endif %}>
            <td class="pos{% if loop.index == 1 %} gold{% endif %}">{{ loop.index }}</td>
            <td>{{ p | trend_prefix }} {{ p.player_name }}</td>
            <td class="num">{{ p.matches_played }}</td>
            <td class="num">{{ p.wins }}</td>
            <td class="num">{{ p.draws }}</td>
            <td class="num">{{ p.losses }}</td>
            <td class="num pts{% if loop.index == 1 %}" style="color:#f0c040;{% endif %}">{{ p.points }}</td>
          </tr>
          {% else %}
          <tr><td colspan="7" style="text-align:center;color:#6c6c9a;padding:8px;">Sin datos</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- Goles y Asistencias lado a lado -->
  <div class="section">
    <div class="split-cols">
      <div>
        <div class="mini-title" style="color:#e74c3c;">
          <span class="dot" style="background:#e74c3c;"></span>Goles
        </div>
        <div class="section-body">
          {% for p in players_by_goals %}
          <div class="bar-row">
            <span class="bar-name">{{ p | trend_prefix }} {{ p.player_name }}</span>
            <div class="bar-track">
              <div class="bar goals" style="width:{{ (p.goals / max_goals * 100) | int }}%;"></div>
            </div>
            <span class="bar-value">{{ p.goals }}</span>
          </div>
          {% else %}
          <div style="text-align:center;color:#6c6c9a;font-size:10px;padding:8px 0;">Sin datos</div>
          {% endfor %}
        </div>
      </div>
      <div>
        <div class="mini-title" style="color:#3498db;">
          <span class="dot" style="background:#3498db;"></span>Asistencias
        </div>
        <div class="section-body">
          {% for p in players_by_assists %}
          <div class="bar-row">
            <span class="bar-name">{{ p | trend_prefix }} {{ p.player_name }}</span>
            <div class="bar-track">
              <div class="bar assists" style="width:{{ (p.assists / max_assists * 100) | int }}%;"></div>
            </div>
            <span class="bar-value">{{ p.assists }}</span>
          </div>
          {% else %}
          <div style="text-align:center;color:#6c6c9a;font-size:10px;padding:8px 0;">Sin datos</div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>

  <!-- Parejas -->
  <div class="section" style="margin-bottom:0;">
    <div class="section-title">🤝 Parejas más frecuentes</div>
    <div class="section-body">
      {% for c in chemistry %}
      <div class="bar-row-wide">
        <span class="bar-name-wide">{{ c.scorer_name }} + {{ c.assistant_name }}</span>
        <div class="bar-track">
          <div class="bar chemistry" style="width:{{ (c.count / max_chemistry * 100) | int }}%;"></div>
        </div>
        <span class="bar-value">{{ c.count }}</span>
      </div>
      {% else %}
      <div style="text-align:center;color:#6c6c9a;font-size:10px;padding:8px 0;">Sin datos</div>
      {% endfor %}
    </div>
  </div>

</div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add pyball/infrastructure/images/stats_template.html
git commit -m "feat(images): add Jinja2 dark-card HTML template for stats"
```

---

### Task 4: Implement StatsHtmlRenderer

**Files:**
- Modify: `pyball/infrastructure/images/stats_renderer.py`

- [ ] **Step 1: Replace the entire file content**

Overwrite `pyball/infrastructure/images/stats_renderer.py` with:

```python
"""Statistics image renderer using Playwright and a Jinja2 HTML template."""

from __future__ import annotations

from pathlib import Path

import jinja2

from playwright.async_api import async_playwright

from pyball.application.meetup.compute_stats import (
    PlayerStats,
    StatsReport,
    StatsScopedReport,
)

_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "stats_template.html"


def _trend_prefix(player: PlayerStats) -> jinja2.Markup:
    """Return an HTML span with the trend symbol for the given player.

    Args:
        player: PlayerStats with rank_delta set.

    Returns:
        Safe HTML Markup with the trend span.
    """
    delta = player.rank_delta
    if delta is None:
        return jinja2.Markup('<span class="trend-new">★</span>')
    if delta > 0:
        return jinja2.Markup('<span class="trend-up">▲</span>')
    if delta < 0:
        return jinja2.Markup('<span class="trend-down">▼</span>')
    return jinja2.Markup('<span class="trend-same">─</span>')


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
```

- [ ] **Step 2: Run the integration tests**

```bash
poetry run pytest tests/integration/test_stats_renderer.py -v
```

Expected output (all 4 pass):
```
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_returns_two_bytes_objects
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_produces_valid_png
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_empty_report_does_not_raise
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_season_and_alltime_images_differ
```

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
make test
```

Expected: all tests pass. The old `test_stats_renderer.py` is gone; the integration test is picked up automatically from `tests/`.

- [ ] **Step 4: Run lint**

```bash
make lint
```

Expected: pylint 10.00/10, no mypy errors, no pydocstyle/pycodestyle failures.

If mypy reports `Cannot find implementation or library stub for module named "playwright"`, confirm the `[tool.mypy.overrides]` section in `pyproject.toml` has `"playwright"` and `"playwright.*"` in the module list (done in Task 1).

- [ ] **Step 5: Commit**

```bash
git add pyball/infrastructure/images/stats_renderer.py
git commit -m "feat(images): replace StatsImageRenderer with StatsHtmlRenderer (Playwright + Jinja2)"
```

---

### Task 5: Wire up app.py

**Files:**
- Modify: `pyball/infrastructure/http/app.py`

- [ ] **Step 1: Update import and call site**

In `pyball/infrastructure/http/app.py`, make two changes:

**Change the import** (line 19):
```python
# Before:
from pyball.infrastructure.images.stats_renderer import StatsImageRenderer

# After:
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
```

**Change the renderer call** inside `_post_match_stats` (line 46):
```python
# Before:
season_png, alltime_png = StatsImageRenderer().render(report)

# After:
season_png, alltime_png = await StatsHtmlRenderer().render(report)
```

- [ ] **Step 2: Run the full test suite**

```bash
make test
```

Expected: all tests pass.

- [ ] **Step 3: Run lint**

```bash
make lint
```

Expected: pylint 10.00/10, no errors.

- [ ] **Step 4: Commit**

```bash
git add pyball/infrastructure/http/app.py
git commit -m "feat(http): use StatsHtmlRenderer in post-match stats task"
```

---

### Task 6: Update Dockerfile

**Files:**
- Modify: `docker/Dockerfile`

- [ ] **Step 1: Add Playwright browser install after pip install**

In `docker/Dockerfile`, replace:

```dockerfile
RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder
```

with:

```dockerfile
RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder \
    && playwright install chromium --with-deps
```

`--with-deps` installs the OS-level system libraries Chromium requires (libglib2, libnss3, libX11, etc.) on the Debian slim base image. Without it the headless browser will fail to launch in the container.

- [ ] **Step 2: Build Docker image to verify**

```bash
make build
```

Expected: image builds without errors. The `playwright install chromium --with-deps` step will download ~300 MB of Chromium + system libs.

- [ ] **Step 3: Commit**

```bash
git add docker/Dockerfile
git commit -m "feat(docker): install Playwright Chromium after pip install"
```
