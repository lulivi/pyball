# WeasyPrint Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Playwright + Chromium with WeasyPrint + pymupdf for HTML→PNG rendering, reducing the Docker image from ~2 GB to ~350–400 MB.

**Architecture:** `StatsHtmlRenderer._screenshot` becomes a synchronous method that renders HTML to PDF via WeasyPrint, converts to PNG via pymupdf, and crops bottom whitespace by scanning for the last non-background row. The public `render()` and `_render_scope()` stay `async` and dispatch `_screenshot` to a thread pool via `asyncio.to_thread()`. The HTML template's `display: grid` is replaced with `display: flex` (WeasyPrint does not support CSS Grid), and a `@page` rule sets the page width.

**Tech Stack:** Python 3.12, WeasyPrint ≥ 60, pymupdf ≥ 1.24 (`fitz`), Jinja2, pytest-asyncio (strict mode), uv, nox.

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Modify | `pyproject.toml` | Swap `playwright` for `weasyprint` + `pymupdf` |
| Modify | `pyball/infrastructure/images/stats_template.html` | CSS grid → flex, add `@page` rule |
| Modify | `pyball/infrastructure/images/stats_renderer.py` | Replace Playwright with WeasyPrint + pymupdf |
| Modify | `docker/Dockerfile` | Remove Playwright install, add WeasyPrint system deps |
| Modify | `tests/integration/test_stats_renderer.py` | Update module docstring |

---

## Task 1: Swap dependencies in pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace `playwright` with `weasyprint` and `pymupdf`**

In `pyproject.toml`, change the `dependencies` list from:

```toml
[project]
dependencies = [
    "python-telegram-bot>=22,<23",
    "pydantic>=2.0,<3",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1,<4",
    "playwright>=1.44,<2",
]
```

to:

```toml
[project]
dependencies = [
    "python-telegram-bot>=22,<23",
    "pydantic>=2.0,<3",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1,<4",
    "weasyprint>=60,<62",
    "pymupdf>=1.24,<2",
]
```

- [ ] **Step 2: Sync the lock file**

```bash
uv sync
```

Expected: `uv.lock` updated, `playwright` removed, `weasyprint` and `pymupdf` installed. No error.

- [ ] **Step 3: Verify playwright is gone and new packages are present**

```bash
uv run python -c "import weasyprint, fitz; print(weasyprint.__version__, fitz.version[0])"
```

Expected: prints two version strings without error.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: replace playwright with weasyprint and pymupdf"
```

---

## Task 2: Fix CSS in the HTML template

**Files:**
- Modify: `pyball/infrastructure/images/stats_template.html`

WeasyPrint does not support `display: grid`. The `.split-cols` section (Goles + Asistencias side by side) must be rewritten as flexbox. The `@page` rule controls the page width WeasyPrint renders at.

- [ ] **Step 1: Add `@page` rule and convert `.split-cols` to flexbox**

Open `pyball/infrastructure/images/stats_template.html`. Inside the `<style>` block, make two changes:

**a)** Add `@page` as the very first rule (before the `*` reset):

```css
@page { size: 390px 600px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
```

**b)** Replace the `.split-cols` rule:

```css
/* before */
.split-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

/* after */
.split-cols { display: flex; gap: 8px; }
.split-cols > div { flex: 1; min-width: 0; }
```

The `min-width: 0` prevents flex children from overflowing when their text content is wide.

- [ ] **Step 2: Commit**

```bash
git add pyball/infrastructure/images/stats_template.html
git commit -m "fix(template): replace CSS grid with flexbox for WeasyPrint compatibility"
```

---

## Task 3: Rewrite the renderer and update the integration test docstring

**Files:**
- Modify: `pyball/infrastructure/images/stats_renderer.py`
- Modify: `tests/integration/test_stats_renderer.py`

The existing integration tests in `tests/integration/test_stats_renderer.py` are the acceptance tests for this task. They verify that `render()` returns two non-empty PNG bytes objects. They will FAIL after Task 1 (playwright removed) and must PASS after this task.

- [ ] **Step 1: Run the integration tests to confirm they fail**

```bash
nox -e test -- tests/integration/test_stats_renderer.py -v
```

Expected: all four async tests FAIL (ImportError or ModuleNotFoundError for playwright).

- [ ] **Step 2: Rewrite `stats_renderer.py`**

Replace the entire file contents with:

```python
"""Statistics image renderer using WeasyPrint and a Jinja2 HTML template."""

from __future__ import annotations

import asyncio
from pathlib import Path

import fitz  # pymupdf
import jinja2
import weasyprint
from markupsafe import Markup

from pyball.application.meetup.compute_stats import StatsReport, StatsScopedReport

_TEMPLATE_DIR = Path(__file__).parent
_TEMPLATE_NAME = "stats_template.html"
_BG_COLOR = bytes([15, 15, 26])  # #0f0f1a — used to detect content rows during crop


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
    """Renders a StatsReport into two PNG images (season and all-time) via WeasyPrint."""

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
        return await asyncio.to_thread(self._screenshot, html)

    def _build_html(self, scoped: StatsScopedReport, title: str) -> str:
        """Render the Jinja2 template with the given scope data.

        Args:
            scoped: Scope-specific stats (players + chemistry).
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

        max_goals = max((p.goals for p in players_by_goals), default=0) or 1
        max_assists = max((p.assists for p in players_by_assists), default=0) or 1
        max_chemistry = max((c.count for c in chemistry), default=0) or 1

        template = _JINJA_ENV.get_template(_TEMPLATE_NAME)
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

    def _screenshot(self, html: str) -> bytes:
        """Render HTML to PNG bytes via WeasyPrint (PDF) and pymupdf.

        Args:
            html: Fully rendered HTML string.

        Returns:
            Raw PNG bytes, cropped to content height.
        """
        pdf = weasyprint.HTML(string=html).write_pdf()
        doc = fitz.open(stream=pdf, filetype="pdf")
        mat = fitz.Matrix(2, 2)
        pixmaps = [page.get_pixmap(matrix=mat) for page in doc]

        if len(pixmaps) == 1:
            full = pixmaps[0]
        else:
            total_h = sum(p.height for p in pixmaps)
            w = pixmaps[0].width
            full = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, total_h), False)
            y = 0
            for p in pixmaps:
                full.copy(p, fitz.IRect(0, y, w, y + p.height))
                y += p.height

        return self._crop_whitespace(full).tobytes("png")

    def _crop_whitespace(self, pix: fitz.Pixmap) -> fitz.Pixmap:
        """Return a new Pixmap with trailing background rows removed.

        Scans from the bottom of the pixmap upward to find the last row
        containing a pixel that differs from the page background color (#0f0f1a).
        Adds 20 px of padding below the last content row.

        Args:
            pix: Source pixmap (RGB, no alpha).

        Returns:
            Cropped pixmap, or the original if no whitespace is found.
        """
        w, h = pix.width, pix.height
        samples = bytes(pix.samples)
        n = pix.n
        last_row = h - 1
        for row in range(h - 1, -1, -1):
            row_bytes = samples[row * w * n : (row + 1) * w * n]
            if any(row_bytes[i * n : i * n + 3] != _BG_COLOR for i in range(w)):
                last_row = row
                break
        crop_h = min(last_row + 21, h)
        if crop_h >= h:
            return pix
        result = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, crop_h), False)
        result.copy(pix, fitz.IRect(0, 0, w, crop_h))
        return result
```

- [ ] **Step 3: Update the integration test module docstring**

In `tests/integration/test_stats_renderer.py`, change line 1 from:

```python
"""Integration tests for StatsHtmlRenderer (requires Playwright + Chromium)."""
```

to:

```python
"""Integration tests for StatsHtmlRenderer (requires WeasyPrint + pymupdf)."""
```

- [ ] **Step 4: Run the integration tests to confirm they pass**

```bash
nox -e test -- tests/integration/test_stats_renderer.py -v
```

Expected: all five tests PASS.

```
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_returns_two_bytes_objects
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_produces_valid_png
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_render_empty_report_does_not_raise
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_season_and_alltime_images_differ
PASSED tests/integration/test_stats_renderer.py::TestStatsHtmlRenderer::test_no_star_symbol_in_html
```

- [ ] **Step 5: Run the full test suite**

```bash
nox -e test
```

Expected: all tests pass, no regressions.

- [ ] **Step 6: Run the linter**

```bash
nox -e lint
```

Expected: all checks pass (black, isort, pydocstyle, pycodestyle, mypy, pylint score 10.00/10).

If mypy reports `Cannot find implementation or library stub for module named "fitz"`, add this section to `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["fitz", "fitz.*"]
ignore_missing_imports = true
```

If mypy reports the same for `weasyprint`, also add:

```toml
[[tool.mypy.overrides]]
module = ["weasyprint", "weasyprint.*"]
ignore_missing_imports = true
```

Then re-run `nox -e lint` to confirm it passes.

- [ ] **Step 7: Commit**

```bash
git add pyball/infrastructure/images/stats_renderer.py \
        tests/integration/test_stats_renderer.py \
        pyproject.toml  # only if mypy overrides were added
git commit -m "feat(images): replace Playwright with WeasyPrint + pymupdf renderer"
```

---

## Task 4: Update the Dockerfile

**Files:**
- Modify: `docker/Dockerfile`

The runtime stage currently installs Playwright and Chromium after the wheel. That line is replaced with the system libraries WeasyPrint needs. pymupdf ships with a statically linked MuPDF wheel — no extra apt packages required for it.

- [ ] **Step 1: Add WeasyPrint system deps to the existing `apt-get install` and remove the Playwright line**

Two changes in `docker/Dockerfile`:

**a)** In the first `RUN` block, add the five WeasyPrint packages to the existing `apt-get install -y locales` line and add `&& rm -rf /var/lib/apt/lists/*` at the end (before the venv commands) to keep the layer clean:

```dockerfile
RUN apt-get update && apt-get install -y \
    locales \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8 \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel
```

**b)** In the second `RUN` block, remove `&& playwright install chromium --with-deps`:

```dockerfile
RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder
```

The full runtime stage after the change:

```dockerfile
FROM python:3.12.13-slim-trixie

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:${PATH}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    locales \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
    && localedef -i es_ES -c -f UTF-8 -A /usr/share/locale/locale.alias es_ES.UTF-8 \
    && /usr/local/bin/python3 -m venv $VIRTUAL_ENV \
    && $VIRTUAL_ENV/bin/python3 -m pip install -U pip wheel

WORKDIR /builder
COPY --from=builder /dist/*.whl .

RUN $VIRTUAL_ENV/bin/python3 -m pip install --no-cache *.whl \
    && rm -rf /builder

WORKDIR /pyball

ENTRYPOINT ["pyball"]
```

- [ ] **Step 2: Commit**

```bash
git add docker/Dockerfile
git commit -m "feat(docker): replace Playwright/Chromium with WeasyPrint system deps"
```

---

## Potential Issues

**pylint `import-error` for `fitz`:** If pylint complains about `fitz`, add it to the pylint disable list or the `extension-pkg-whitelist` in the pylint config. More likely pylint will resolve it correctly since pymupdf registers `fitz` as a proper package.

**WeasyPrint font fallback:** Without `fonts-noto-color-emoji`, the 🏆 and 🤝 emojis render as boxes. This is only an issue outside Docker (local dev). The Dockerfile installs this package so production is fine. To install locally on Debian/Ubuntu: `sudo apt-get install fonts-noto-color-emoji`.

**Content taller than 600px CSS:** If the content (e.g., 10 players in every category) exceeds the 600px page height, WeasyPrint will create a second PDF page. The `_screenshot` method handles multi-page PDFs by stacking pages vertically before cropping — this works correctly.
