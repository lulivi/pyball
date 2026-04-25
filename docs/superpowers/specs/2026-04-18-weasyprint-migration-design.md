# WeasyPrint Migration Design

**Date:** 2026-04-18
**Goal:** Replace Playwright + Chromium with WeasyPrint + pymupdf for HTML→PNG rendering,
reducing the Docker image from ~2 GB to ~350-400 MB.

## Context

`StatsHtmlRenderer` renders a Jinja2 HTML template to PNG and sends it to Telegram.
Currently it uses Playwright's headless Chromium, which adds ~1.5 GB to the Docker image
via `playwright install chromium --with-deps`.

WeasyPrint is a pure-Python HTML/CSS renderer that outputs PDF. pymupdf converts that PDF
to PNG. Neither requires a browser binary.

**Important:** WeasyPrint dropped PNG output in v53 — it only generates PDF today. pymupdf
(~50 MB wheel with statically linked MuPDF) converts PDF pages to PNG.

## Architecture

```
HTML string
    │
    ▼
weasyprint.HTML(string=html).write_pdf()  → PDF bytes
    │
    ▼
fitz.open(stream=pdf_bytes)               → Document (pymupdf)
    │  for each page → page.get_pixmap(matrix=2×) → pixmap
    │  stack pixmaps vertically
    ▼
PNG bytes
```

`_screenshot` is synchronous. `render()` and `_render_scope()` stay `async` and call
`_screenshot` via `asyncio.to_thread()` to avoid blocking the event loop.

## Changes

### `pyproject.toml`
- Remove `playwright>=1.44,<2`
- Add `weasyprint>=60,<62`
- Add `pymupdf>=1.24,<2`
- Remove `playwright.*` from `[tool.mypy.overrides]` ignore list (no longer needed)
- Add `fitz` to mypy ignore list (pymupdf's import name, no type stubs)

### `stats_template.html`
- **CSS Grid → Flexbox:** WeasyPrint does not support `display: grid`.
  Replace `.split-cols` rule:
  ```css
  /* before */
  .split-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  /* after */
  .split-cols { display: flex; gap: 8px; }
  .split-cols > div { flex: 1; min-width: 0; }
  ```
- **`@page` rule:** Set page width to match the mobile design and remove margins:
  ```css
  @page { size: 390px auto; margin: 0; }
  ```
  This tells WeasyPrint the page width is 390 px; height is determined by content.

### `stats_renderer.py`
- Remove `playwright` import
- Add `import asyncio`, `import fitz`, `import weasyprint`
- `_screenshot(self, html: str) -> bytes` becomes a regular (sync) method:
  ```python
  def _screenshot(self, html: str) -> bytes:
      pdf = weasyprint.HTML(string=html).write_pdf()
      doc = fitz.open(stream=pdf, filetype="pdf")
      mat = fitz.Matrix(2, 2)
      pixmaps = [page.get_pixmap(matrix=mat) for page in doc]
      if len(pixmaps) == 1:
          return pixmaps[0].tobytes("png")
      # Stack pages vertically (rare: only if content overflows one page)
      total_height = sum(p.height for p in pixmaps)
      width = pixmaps[0].width
      combined = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, total_height))
      y = 0
      for pix in pixmaps:
          combined.copy(pix, fitz.IRect(0, y, width, y + pix.height))
          y += pix.height
      return combined.tobytes("png")
  ```
- `_render_scope` becomes `async` and calls `_screenshot` via `asyncio.to_thread`:
  ```python
  async def _render_scope(self, scoped, title):
      html = self._build_html(scoped, title)
      return await asyncio.to_thread(self._screenshot, html)
  ```
- Update class and `_screenshot` docstrings to remove Playwright references.

### `docker/Dockerfile`
- Remove `&& playwright install chromium --with-deps`
- Add system libraries WeasyPrint needs to the existing `apt-get install` line:
  `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 fonts-noto-color-emoji`
- pymupdf ships a statically linked MuPDF wheel — no extra apt packages needed for it.

### `tests/integration/test_stats_renderer.py`
- Update module docstring: remove "requires Playwright + Chromium".

## Scope: Playwright mentions in other files

No `README.md` or `AGENTS.md` contain Playwright references. All remaining mentions
(`docs/superpowers/specs/`, `docs/superpowers/plans/`) are historical design/plan
documents that record past decisions and are intentionally left unchanged.

## Out of scope

- Visual fidelity comparison between Chromium and WeasyPrint renders (not a regression test)
- Font changes (system fonts used by WeasyPrint will differ from Chromium's Segoe UI/system-ui)

## Testing

- Existing unit tests (`tests/unit/infrastructure/test_stats_renderer.py`) test `_build_html`
  and `_trend_prefix` — no changes needed.
- Existing integration tests (`tests/integration/test_stats_renderer.py`) test `render()` —
  they check PNG magic bytes and non-empty output. These will pass with WeasyPrint + pymupdf
  since the interface and return type are unchanged.
- Dev environment: `nox -e test` will run the integration tests locally (WeasyPrint + pymupdf
  must be installed; no browser binary needed).
