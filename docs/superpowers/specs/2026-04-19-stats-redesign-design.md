# Stats Redesign Design

**Date:** 2026-04-19
**Branch:** feature/pyball-v4

## Overview

Three related changes to the post-match stats system:

1. Match finish sends only the season stats image (not all-time)
2. New admin command `/stats [temporada|historico]` for on-demand stats
3. Template redesign: neon aesthetic, rename "Parejas más frecuentes" → "La Dupla", new "Dúo Ganador" section

## 1. Renderer API Change

`StatsHtmlRenderer.render()` changes signature:

```python
# Before
async def render(self, report: StatsReport) -> tuple[bytes, bytes]

# After
async def render(self, report: StatsReport, scope: str = "season") -> bytes
```

- `scope="season"` renders `report.season` with title `"Esta temporada"`
- `scope="alltime"` renders `report.all_time` with title `"Histórico"`
- The internal `_render_scope` method remains unchanged

`_post_match_stats` in `app.py` calls `render(report, scope="season")` and sends a single photo.

## 2. New Data: Winning Pairs

### New dataclass in `compute_stats.py`

```python
@dataclass
class WinningPair:
    player_a_name: str
    player_b_name: str
    count: int
```

### Extended `StatsScopedReport`

```python
@dataclass
class StatsScopedReport:
    players: list[PlayerStats]
    chemistry: list[ChemistryPair]
    winning_pairs: list[WinningPair]  # new
```

### Computation in `_aggregate`

For each finished meetup with a result:
- Identify the winning team — skip the meetup entirely if it ended in a draw (draws produce no winning pair)
- Generate all 2-player combinations from the winning team's player list
- Increment count for each pair (stored as a frozenset or sorted tuple to avoid duplicates)

In `_build_scoped_report`, sort by count descending, resolve player names, return top 5 as `WinningPair` list.

## 3. New Admin Command `/stats`

### Handler location

New handler function in `pyball/bot/handlers/meetup.py` (or a new file if it grows large) registered as a `CommandHandler` for `"stats"`.

### Behavior

```
/stats temporada   → season stats image
/stats historico   → all-time stats image
(no arg / bad arg) → Spanish help message: "Usa /stats temporada o /stats historico"
```

- Decorated with `@authorized` (admin-only)
- Calls `ComputeStats(...).execute()` then `StatsHtmlRenderer().render(report, scope=...)`
- Sends the resulting PNG via `update.message.reply_photo`

### Command registration

Registered in `bot/entrypoint.py` alongside existing command handlers.

## 4. Template Redesign

### Visual style — Neon

| Element | Before | After |
|---------|--------|-------|
| Page background | `#0f0f1a` | `#080810` |
| Card/section bg | `#1a1a2e` | `#0f0f20` |
| Title color | `#a0a0c0` | gradient text (pink→purple) |
| Section labels | `#6c6c9a` | vibrant (blue/pink per section) |
| Goal bars | solid `#e74c3c` | gradient `#f72585 → #7209b7` |
| Assist bars | solid `#3498db` | gradient `#3a86ff → #4cc9f0` |
| Chemistry bars | solid `#2ecc71` | gradient `#06d6a0 → #118ab2` |
| Winning pair bars | n/a | gradient `#ffd166 → #ef476f` |
| Row accent | none | left border colored per section |
| Gold (1st place) | `#f0c040` | `#ffd166` |

### Content changes

- **"Parejas más frecuentes"** renamed to **"La Dupla"** — same `chemistry` data, same bar layout
- New section **"Dúo Ganador"** added after "La Dupla":
  - Same wide-bar layout as "La Dupla"
  - Shows `winning_pairs`: player A + player B, bar proportional to count
  - Bar color: gold gradient `#ffd166 → #ef476f`
  - "Sin datos" fallback if no winning pairs exist

## Files Changed

| File | Change |
|------|--------|
| `pyball/application/meetup/compute_stats.py` | Add `WinningPair` dataclass, `winning_pairs` field to `StatsScopedReport`, compute winning pairs in `_aggregate` and `_build_scoped_report` |
| `pyball/infrastructure/images/stats_renderer.py` | Change `render()` signature to accept `scope` param, return single `bytes` |
| `pyball/infrastructure/images/stats_template.html` | Neon redesign, rename section, add "Dúo Ganador" section |
| `pyball/infrastructure/http/app.py` | Update `_post_match_stats` to use `render(report, scope="season")`, send single photo |
| `pyball/bot/handlers/meetup.py` | Add `/stats` command handler with `@authorized` |
| `pyball/bot/entrypoint.py` | Register `/stats` `CommandHandler` |
| `tests/unit/application/test_meetup_use_cases.py` | Add tests for `WinningPair` computation |
| `tests/unit/infrastructure/test_stats_renderer.py` | Update renderer tests for new signature |
| `tests/integration/test_stats_renderer.py` | Update for new signature |

## Out of Scope

- No changes to the HTTP API (`/api/match/finish` endpoint behavior is unchanged except it triggers one photo instead of two)
- No new Telegram slash command registration in BotFather (user handles that separately)
- No changes to the `ComputeStats` use case interface beyond `StatsScopedReport`
