# HTML Stats Renderer Design

**Date:** 2026-04-14
**Branch:** feature/pyball-v4

## Goal

Replace the existing `StatsImageRenderer` (matplotlib) with a new `StatsHtmlRenderer`
that renders a Jinja2 HTML template and captures it as a PNG via Playwright's headless
Chromium. The result is a visually polished dark-card stats image sent to Telegram after
each match, indistinguishable from a native mobile app screenshot.

---

## Visual Design

**Style:** Dark card — background `#0f0f1a`, dark-blue section backgrounds `#1a1a2e`,
alternating odd rows `#1f1f38`. Accent colours: gold `#f0c040` (rank 1 / points),
red `#e74c3c` (goals), blue `#3498db` (assists), green `#2ecc71` (chemistry/parejas).

**Viewport:** 390 × 844 px logical (iPhone 14/15 standard), `device_scale_factor=2`
→ PNG output is **780 px wide** at 2× resolution, crisp on Retina/AMOLED screens.
`full_page=True` on the Playwright screenshot so height adjusts to content.

**Layout (vertical, single column):**

| Section | Content | Limit |
|---------|---------|-------|
| 🏆 Clasificación | Table: #, Jugador, PJ, G, E, P, Pts | Top 10 |
| ⚽ Goles / 🅰️ Asistencias | Two side-by-side bar rankings | Top 10 each |
| 🤝 Parejas más frecuentes | Horizontal bar chart | Top 5 |

Player name labels in clasificación and both bar rankings include a trend prefix:
`▲` (moved up, green), `▼` (dropped, red), `─` (no change, grey), `★` (new entry, gold).
Chemistry pair labels have no prefix (pairs have no rank delta).

Two images are generated per match: `"Esta temporada"` and `"Histórico"`.

---

## File Changes

| Action | File | Purpose |
|--------|------|---------|
| Delete | `pyball/infrastructure/images/stats_renderer.py` | Remove `StatsImageRenderer` / matplotlib |
| Create | `pyball/infrastructure/images/stats_renderer.py` | New `StatsHtmlRenderer` |
| Create | `pyball/infrastructure/images/stats_template.html` | Jinja2 dark-card template |
| Modify | `pyball/application/container.py` | Instantiate `StatsHtmlRenderer` |
| Modify | `pyball/bot/handlers/meetup.py` | `await renderer.render(report)` |
| Modify | `pyproject.toml` | Remove `matplotlib`; add `playwright`, `jinja2` |
| Modify | `docker/Dockerfile` | Add `playwright install chromium --with-deps` |
| Move | `tests/unit/infrastructure/test_stats_renderer.py` → `tests/integration/` | Requires real browser |

---

## Application Layer: No Changes

`ComputeStats` and all `StatsReport` / `PlayerStats` / `ChemistryPair` data structures
remain unchanged. `StatsHtmlRenderer` consumes the same `StatsReport` as input.

---

## Infrastructure Layer: `StatsHtmlRenderer`

**File:** `pyball/infrastructure/images/stats_renderer.py`

```python
class StatsHtmlRenderer:
    async def render(self, report: StatsReport) -> tuple[bytes, bytes]:
        """Generate PNG images for season and all-time scopes."""
        season_png = await self._render_scope(report.season, "Esta temporada")
        all_time_png = await self._render_scope(report.all_time, "Histórico")
        return season_png, all_time_png

    async def _render_scope(self, scoped: StatsScopedReport, title: str) -> bytes:
        html = self._build_html(scoped, title)
        return await self._screenshot(html)

    def _build_html(self, scoped: StatsScopedReport, title: str) -> str:
        # Loads stats_template.html from same directory via Path(__file__).parent
        # Registers trend_prefix as a Jinja2 filter
        # Renders with: title, players (top 10), players_by_goals (top 10),
        #   players_by_assists (top 10), chemistry (top 5),
        #   max_goals, max_assists, max_chemistry

    async def _screenshot(self, html: str) -> bytes:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
            )
            await page.set_content(html, wait_until="load")
            png = await page.screenshot(full_page=True)
            await browser.close()
            return png
```

**Template variables passed to Jinja2:**

| Variable | Type | Description |
|----------|------|-------------|
| `title` | `str` | `"Esta temporada"` or `"Histórico"` |
| `players` | `list[PlayerStats]` | Sorted by points desc, max 10 |
| `players_by_goals` | `list[PlayerStats]` | Sorted by goals desc, max 10 |
| `players_by_assists` | `list[PlayerStats]` | Sorted by assists desc, max 10 |
| `chemistry` | `list[ChemistryPair]` | Sorted by count desc, max 5 |
| `max_goals` | `int` | Highest goals value (for bar width %) |
| `max_assists` | `int` | Highest assists value (for bar width %) |
| `max_chemistry` | `int` | Highest chemistry count (for bar width %) |

The `trend_prefix` Jinja2 filter maps `rank_delta` → `▲ / ▼ / ─ / ★` with the
corresponding CSS class (`trend-up / trend-down / trend-same / trend-new`).

**Edge case — empty data:** when `max_goals`, `max_assists`, or `max_chemistry` is 0
(no stats recorded), `_build_html` passes `max_goals=1` etc. as a safe default so the
template never divides by zero. Bar widths will be 0% for all rows, which renders
correctly as empty bars.

**Template:** `pyball/infrastructure/images/stats_template.html`

A self-contained HTML document with all CSS inline (no external fonts or assets).
Structure:

```
<html>
  <head> — charset, viewport meta, inline CSS (dark card theme) </head>
  <body>
    <div class="card">
      <h1>{{ title }}</h1>

      <!-- Clasificación -->
      <section>
        <h2>🏆 Clasificación</h2>
        <table>
          <thead> # / Jugador / PJ / G / E / P / Pts </thead>
          <tbody>
            {% for p in players %}
            <tr class="{{ 'odd' if loop.index is odd }}">
              <td>{{ loop.index }}</td>
              <td>{{ p | trend_prefix }} {{ p.player_name }}</td>
              <td>{{ p.matches_played }}</td>
              <td>{{ p.wins }}</td>
              <td>{{ p.draws }}</td>
              <td>{{ p.losses }}</td>
              <td>{{ p.points }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>

      <!-- Goles y Asistencias (lado a lado) -->
      <section class="split">
        <div>  <!-- Goles -->
          {% for p in players_by_goals %}
          <div class="bar-row">
            <span>{{ p | trend_prefix }} {{ p.player_name }}</span>
            <div class="bar goals" style="width:{{ p.goals / max_goals * 100 }}%"></div>
            <span>{{ p.goals }}</span>
          </div>
          {% endfor %}
        </div>
        <div>  <!-- Asistencias -->
          {% for p in players_by_assists %}
          <div class="bar-row">
            <span>{{ p | trend_prefix }} {{ p.player_name }}</span>
            <div class="bar assists" style="width:{{ p.assists / max_assists * 100 }}%"></div>
            <span>{{ p.assists }}</span>
          </div>
          {% endfor %}
        </div>
      </section>

      <!-- Parejas -->
      <section>
        {% for c in chemistry %}
        <div class="bar-row">
          <span>{{ c.scorer_name }} + {{ c.assistant_name }}</span>
          <div class="bar chemistry" style="width:{{ c.count / max_chemistry * 100 }}%"></div>
          <span>{{ c.count }}</span>
        </div>
        {% endfor %}
      </section>
    </div>
  </body>
</html>
```

---

## Bot Integration Changes

### `pyball/application/container.py`

Replace `StatsImageRenderer` with `StatsHtmlRenderer` — one import and one instantiation
change.

### `pyball/bot/handlers/meetup.py`

The existing `_post_match_stats` async helper calls `renderer.render(report)` synchronously.
Change to `await renderer.render(report)`. Error handling (catch, log, drop) is unchanged.

---

## Dependencies

### `pyproject.toml`

```toml
# Remove:
matplotlib = "..."

# Add:
jinja2 = "^3.1"
playwright = "^1.44"
```

### `docker/Dockerfile`

After `poetry install`:

```dockerfile
RUN poetry run playwright install chromium --with-deps
```

`--with-deps` installs the system libraries Chromium requires (libglib, libnss, libX11,
etc.) so the headless browser works inside the container without additional OS packages.

---

## Testing

### Integration test (moved from unit)

**File:** `tests/integration/test_stats_renderer.py`

```python
@pytest.mark.asyncio
async def test_render_returns_two_png_bytes():
    report = _minimal_stats_report()
    renderer = StatsHtmlRenderer()
    season_png, all_time_png = await renderer.render(report)
    assert isinstance(season_png, bytes) and len(season_png) > 0
    assert isinstance(all_time_png, bytes) and len(all_time_png) > 0

@pytest.mark.asyncio
async def test_render_does_not_raise_with_empty_data():
    report = StatsReport(
        season=StatsScopedReport(players=[], chemistry=[]),
        all_time=StatsScopedReport(players=[], chemistry=[]),
    )
    season_png, all_time_png = await StatsHtmlRenderer().render(report)
    assert len(season_png) > 0
    assert len(all_time_png) > 0
```

Playwright must be installed in the test environment (`playwright install chromium`).
These tests are excluded from the fast unit test run and only executed in the integration
nox session (or CI with the full Docker image).

### Unit tests unchanged

`tests/unit/application/test_compute_stats.py` — no changes needed. The rendering layer
is fully decoupled from stats computation.
