# Stats Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send only season stats on match finish, add `/stats [temporada|historico]` admin command, rename "Parejas más frecuentes" → "La Dupla", add "Dúo Ganador" section (winning teammate pairs), and redesign the template with a neon aesthetic.

**Architecture:** `WinningPair` is added to `compute_stats.py` alongside `ChemistryPair`; `StatsScopedReport` gains a `winning_pairs` field with a default so existing tests keep compiling. `StatsHtmlRenderer.render()` gains a `scope` param and returns a single `bytes` instead of a tuple. The `/stats` handler in `meetup.py` calls `ComputeStats` then `StatsHtmlRenderer` directly.

**Tech Stack:** Python 3.12, pytest-asyncio (strict mode), WeasyPrint + pymupdf, Jinja2, python-telegram-bot.

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `pyball/application/meetup/compute_stats.py` | Modify | Add `WinningPair`, `winning_pairs` field to `StatsScopedReport`, compute winning pairs in `_aggregate` |
| `pyball/infrastructure/images/stats_renderer.py` | Modify | `render()` → `render(report, scope="season") -> bytes` |
| `pyball/infrastructure/images/stats_template.html` | Modify | Neon design, rename section, add Dúo Ganador |
| `pyball/infrastructure/http/app.py` | Modify | Send one photo with `scope="season"` |
| `pyball/bot/handlers/meetup.py` | Modify | Add `stats_handler`, register in `setup_meetup_handlers` |
| `tests/unit/application/test_compute_stats.py` | Modify | Add `TestComputeStatsWinningPairs` class |
| `tests/unit/infrastructure/test_stats_renderer.py` | Modify | Update CSS anchor strings, add `winning_pairs=[]` to `StatsScopedReport` calls |
| `tests/integration/test_stats_renderer.py` | Modify | Update render() call sites (tuple → single bytes) |
| `tests/integration/bot/test_meetup_handlers.py` | Modify | Add `/stats` handler tests |

---

## Task 1: Add WinningPair to compute_stats (TDD)

**Files:**
- Modify: `pyball/application/meetup/compute_stats.py`
- Modify: `tests/unit/application/test_compute_stats.py`

- [ ] **Step 1: Write failing tests for WinningPair**

Add at the bottom of `tests/unit/application/test_compute_stats.py`:

```python
class TestComputeStatsWinningPairs:
    """Winning teammate pair counting."""

    def test_winning_pair_counted_from_winning_team(self):
        """Two players on the winning team increment their winning-pair count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 2, 1
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.winning_pairs) == 1
        wp = report.all_time.winning_pairs[0]
        assert {wp.player_a_name, wp.player_b_name} == {"Alice", "Bob"}
        assert wp.count == 1

    def test_draw_produces_no_winning_pairs(self):
        """A drawn match contributes no winning pairs."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert not report.all_time.winning_pairs

    def test_winning_pairs_sorted_by_count_desc(self):
        """Winning pairs are returned sorted by count descending."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        # alice+bob win together twice; alice+charlie win once
        m1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0)
        m2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0)
        m3 = make_meetup(datetime(2026, 1, 24, 20, 0), [alice.id, charlie.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([m1, m2, m3], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        pairs = report.all_time.winning_pairs
        assert {pairs[0].player_a_name, pairs[0].player_b_name} == {"Alice", "Bob"}
        assert pairs[0].count == 2

    def test_winning_pairs_capped_at_five(self):
        """Only top 5 winning pairs are returned."""
        players = [make_player(f"P{i}") for i in range(12)]
        meetups = []
        day = 1
        # Create 6 distinct winning pairs with different counts
        for i in range(6):
            pa, pb = players[i * 2], players[i * 2 + 1]
            for _ in range(i + 1):
                m = make_meetup(
                    datetime(2026, 3, day, 20, 0), [pa.id, pb.id], [players[0].id], 1, 0
                )
                meetups.append(m)
                day = (day % 28) + 1
        meetup_repo, player_repo = make_repos(meetups, players)
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.winning_pairs) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -e test -- tests/unit/application/test_compute_stats.py::TestComputeStatsWinningPairs -v
```

Expected: `AttributeError: type object 'StatsScopedReport' has no attribute 'winning_pairs'` or similar.

- [ ] **Step 3: Add WinningPair dataclass and update StatsScopedReport**

In `pyball/application/meetup/compute_stats.py`, change the top imports and dataclasses:

```python
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import date
```

Add `WinningPair` after `ChemistryPair`:

```python
@dataclass
class WinningPair:
    """A pair of players who won together most often."""

    player_a_name: str
    player_b_name: str
    count: int
```

Update `StatsScopedReport` to add the new field with a default:

```python
@dataclass
class StatsScopedReport:
    """Statistics for a single time scope (season or all-time)."""

    players: list[PlayerStats]
    chemistry: list[ChemistryPair]
    winning_pairs: list[WinningPair] = field(default_factory=list)
```

- [ ] **Step 4: Update _aggregate to track winning pairs**

Replace the full `_aggregate` function:

```python
def _aggregate(
    meetups: list,
) -> tuple[dict[str, dict], dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    """Aggregate raw stats from a list of meetups.

    Returns:
        Tuple of (player_data, chemistry_counts, winning_counts) where
        player_data maps player_id to stat counters, chemistry_counts maps
        (scorer_id, assistant_id) to occurrence count, and winning_counts maps
        sorted (player_id_a, player_id_b) to co-win count.
    """
    player_data: dict[str, dict] = {}
    chemistry_counts: dict[tuple[str, str], int] = {}
    winning_counts: dict[tuple[str, str], int] = {}

    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue

        score_a = meetup.result.score_a
        score_b = meetup.result.score_b

        for team in meetup.teams:
            team_wins = (team.name == "A" and score_a > score_b) or (
                team.name == "B" and score_b > score_a
            )
            team_draws = score_a == score_b

            for player_id in team.players:
                pid = str(player_id.value)
                if pid not in player_data:
                    player_data[pid] = _empty_counters()
                player_data[pid]["mp"] += 1
                if team_wins:
                    player_data[pid]["w"] += 1
                elif team_draws:
                    player_data[pid]["d"] += 1
                else:
                    player_data[pid]["l"] += 1

            if team_wins:
                for pid_a, pid_b in itertools.combinations(team.players, 2):
                    pair = tuple(sorted([str(pid_a.value), str(pid_b.value)]))
                    winning_counts[pair] = winning_counts.get(pair, 0) + 1

        for event in meetup.result.events:
            scorer_id = str(event.scorer_id.value)
            if scorer_id not in player_data:
                player_data[scorer_id] = _empty_counters()
            player_data[scorer_id]["goals"] += 1

            if event.assistant_id is not None:
                assistant_id = str(event.assistant_id.value)
                if assistant_id not in player_data:
                    player_data[assistant_id] = _empty_counters()
                player_data[assistant_id]["assists"] += 1
                pair_chem = (scorer_id, assistant_id)
                chemistry_counts[pair_chem] = chemistry_counts.get(pair_chem, 0) + 1

    return player_data, chemistry_counts, winning_counts
```

- [ ] **Step 5: Update _build_scoped_report to unpack 3-tuple and build winning_pairs**

Replace the full `_build_scoped_report` function:

```python
def _build_scoped_report(
    meetups: list,
    player_names: dict[str, str],
    prev_meetups: list | None = None,
) -> StatsScopedReport:
    """Build a StatsScopedReport, computing rank deltas from prev_meetups if provided."""
    player_data, chemistry_counts, winning_counts = _aggregate(meetups)

    stats_list = [
        PlayerStats(
            player_id=pid,
            player_name=player_names.get(pid, pid),
            goals=d["goals"],
            assists=d["assists"],
            matches_played=d["mp"],
            wins=d["w"],
            draws=d["d"],
            losses=d["l"],
            points_rank_delta=None,
            goals_rank_delta=None,
            assists_rank_delta=None,
        )
        for pid, d in player_data.items()
    ]
    stats_list.sort(key=lambda p: (-p.points, p.player_name))

    if prev_meetups is not None:
        prev_data, _, _ = _aggregate(prev_meetups)

        prev_pts_ranked = sorted(
            [pid for pid, d in prev_data.items() if _points_from_counters(d) > 0],
            key=lambda pid: (-_points_from_counters(prev_data[pid]), player_names.get(pid, pid)),
        )
        prev_pts_rank = {pid: i + 1 for i, pid in enumerate(prev_pts_ranked)}
        for i, player in enumerate([p for p in stats_list if p.points > 0]):
            if player.player_id in prev_pts_rank:
                player.points_rank_delta = prev_pts_rank[player.player_id] - (i + 1)

        prev_goals_ranked = sorted(
            [pid for pid, d in prev_data.items() if d["goals"] > 0],
            key=lambda pid: (-prev_data[pid]["goals"], player_names.get(pid, pid)),
        )
        prev_goals_rank = {pid: i + 1 for i, pid in enumerate(prev_goals_ranked)}
        current_goals = sorted(
            [p for p in stats_list if p.goals > 0],
            key=lambda p: (-p.goals, p.player_name),
        )
        for i, player in enumerate(current_goals):
            if player.player_id in prev_goals_rank:
                player.goals_rank_delta = prev_goals_rank[player.player_id] - (i + 1)

        prev_assists_ranked = sorted(
            [pid for pid, d in prev_data.items() if d["assists"] > 0],
            key=lambda pid: (-prev_data[pid]["assists"], player_names.get(pid, pid)),
        )
        prev_assists_rank = {pid: i + 1 for i, pid in enumerate(prev_assists_ranked)}
        current_assists = sorted(
            [p for p in stats_list if p.assists > 0],
            key=lambda p: (-p.assists, p.player_name),
        )
        for i, player in enumerate(current_assists):
            if player.player_id in prev_assists_rank:
                player.assists_rank_delta = prev_assists_rank[player.player_id] - (i + 1)

    chemistry = sorted(
        [
            ChemistryPair(
                scorer_name=player_names.get(scorer_id, scorer_id),
                assistant_name=player_names.get(assistant_id, assistant_id),
                count=cnt,
            )
            for (scorer_id, assistant_id), cnt in chemistry_counts.items()
        ],
        key=lambda c: c.count,
        reverse=True,
    )[:10]

    winning_pairs = sorted(
        [
            WinningPair(
                player_a_name=player_names.get(pid_a, pid_a),
                player_b_name=player_names.get(pid_b, pid_b),
                count=cnt,
            )
            for (pid_a, pid_b), cnt in winning_counts.items()
        ],
        key=lambda wp: wp.count,
        reverse=True,
    )[:5]

    return StatsScopedReport(
        players=stats_list, chemistry=chemistry, winning_pairs=winning_pairs
    )
```

- [ ] **Step 6: Run the new tests and verify they pass**

```bash
nox -e test -- tests/unit/application/test_compute_stats.py -v
```

Expected: all tests pass, including the new `TestComputeStatsWinningPairs` class.

- [ ] **Step 7: Commit**

```bash
git add pyball/application/meetup/compute_stats.py tests/unit/application/test_compute_stats.py
git commit -m "feat(stats): add WinningPair — winning teammate pair computation"
```

---

## Task 2: Update StatsHtmlRenderer.render() signature (TDD)

**Files:**
- Modify: `pyball/infrastructure/images/stats_renderer.py`
- Modify: `tests/unit/infrastructure/test_stats_renderer.py`
- Modify: `tests/integration/test_stats_renderer.py`

- [ ] **Step 1: Update unit test helper to include winning_pairs**

In `tests/unit/infrastructure/test_stats_renderer.py`, update `TestBuildHtml._build`:

```python
def _build(self, players, chemistry=None, winning_pairs=None) -> str:
    """Build HTML from a player list."""
    scoped = StatsScopedReport(
        players=sorted(players, key=lambda p: p.points, reverse=True),
        chemistry=chemistry or [],
        winning_pairs=winning_pairs or [],
    )
    return StatsHtmlRenderer()._build_html(scoped, "Test")
```

Also update the import at the top to include `WinningPair`:

```python
from pyball.application.meetup.compute_stats import PlayerStats, StatsScopedReport, WinningPair
```

- [ ] **Step 2: Update integration tests to expect single bytes**

Replace the full contents of `tests/integration/test_stats_renderer.py`:

```python
"""Integration tests for StatsHtmlRenderer (requires WeasyPrint + pymupdf)."""

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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
nox -e test -- tests/integration/test_stats_renderer.py -v
```

Expected: `TypeError` or `ValueError` because `render()` still returns a tuple.

- [ ] **Step 4: Update StatsHtmlRenderer.render() in stats_renderer.py**

Replace the `render` method:

```python
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
    return await self._render_scope(report.season, "Esta temporada")
```

Also add `winning_pairs` and `max_winning` to `_build_html`:

```python
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
```

- [ ] **Step 5: Run all renderer tests**

```bash
nox -e test -- tests/unit/infrastructure/test_stats_renderer.py tests/integration/test_stats_renderer.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add pyball/infrastructure/images/stats_renderer.py \
        tests/unit/infrastructure/test_stats_renderer.py \
        tests/integration/test_stats_renderer.py
git commit -m "feat(renderer): change render() to return single scope PNG"
```

---

## Task 3: Redesign template (neon + rename + Dúo Ganador) and fix unit tests

**Files:**
- Modify: `pyball/infrastructure/images/stats_template.html`
- Modify: `tests/unit/infrastructure/test_stats_renderer.py`

- [ ] **Step 1: Replace stats_template.html with neon redesign**

Replace the full contents of `pyball/infrastructure/images/stats_template.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=390">
<style>
@page { size: 390px 1200px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #080810;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  color: #fff;
}
.card { background: #080810; padding: 20px; }
.card-title {
  text-align: center;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 3px;
  color: #fff;
  text-transform: uppercase;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f72585;
}
.section { margin-bottom: 16px; }
.section-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 6px;
}
.section-body {
  background: #0f0f20;
  border-radius: 6px;
  padding: 8px 10px;
  border-left: 2px solid currentColor;
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
.ranking-table tbody tr.odd { background: #141428; }
.ranking-table tbody td { padding: 4px; }
.ranking-table .pos { color: #6c6c9a; width: 18px; }
.ranking-table .pos.gold { color: #ffd166; }
.ranking-table .num { text-align: center; color: #c0c0d0; }
.ranking-table .pts { text-align: center; font-weight: 700; }
.ranking-table .pts.gold { color: #ffd166; }
/* Trend symbols */
.trend-up { color: #2ecc71; }
.trend-down { color: #e74c3c; }
.trend-same { color: #6c6c9a; }
/* Split columns (goles / asistencias) */
.split-cols { display: flex; gap: 8px; }
.split-cols > div { flex: 1; min-width: 0; }
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
.bar.goals { background: linear-gradient(90deg, #f72585, #7209b7); }
.bar.assists { background: linear-gradient(90deg, #3a86ff, #4cc9f0); }
.bar.chemistry { background: linear-gradient(90deg, #06d6a0, #118ab2); }
.bar.winning { background: linear-gradient(90deg, #ffd166, #ef476f); }
.bar-value { font-size: 9px; color: #6c6c9a; white-space: nowrap; }
/* Wide bar rows */
.bar-row-wide { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.bar-row-wide:last-child { margin-bottom: 0; }
.bar-name-wide {
  font-size: 11px;
  color: #d0d0e0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 160px;
}
</style>
</head>
<body>
<div class="card">
  <div class="card-title">{{ title }}</div>

  <!-- Clasificación -->
  <div class="section">
    <div class="section-title" style="color:#3a86ff;">🏆 Clasificación</div>
    <div class="section-body" style="border-left-color:#3a86ff;">
      <table class="ranking-table">
        <thead>
          <tr>
            <td class="pos">#</td>
            <td>Jugador</td>
            <td class="num">PJ</td>
            <td class="num">G</td>
            <td class="num">E</td>
            <td class="num">P</td>
            <td class="num" style="color:#ffd166;">Pts</td>
          </tr>
        </thead>
        <tbody>
          {% for p in players %}
          <tr{% if loop.index is odd %} class="odd"{% endif %}>
            <td class="pos{% if loop.index == 1 %} gold{% endif %}">{{ loop.index }}</td>
            <td>{{ p.points_rank_delta | trend_prefix }} {{ p.player_name }}</td>
            <td class="num">{{ p.matches_played }}</td>
            <td class="num">{{ p.wins }}</td>
            <td class="num">{{ p.draws }}</td>
            <td class="num">{{ p.losses }}</td>
            <td class="num pts{% if loop.index == 1 %} gold{% endif %}">{{ p.points }}</td>
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
        <div class="mini-title" style="color:#f72585;">
          <span class="dot" style="background:#f72585;"></span>Goles
        </div>
        <div class="section-body" style="border-left-color:#f72585;">
          {% for p in players_by_goals %}
          <div class="bar-row">
            <span class="bar-name">{{ p.goals_rank_delta | trend_prefix }} {{ p.player_name }}</span>
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
        <div class="mini-title" style="color:#3a86ff;">
          <span class="dot" style="background:#3a86ff;"></span>Asistencias
        </div>
        <div class="section-body" style="border-left-color:#3a86ff;">
          {% for p in players_by_assists %}
          <div class="bar-row">
            <span class="bar-name">{{ p.assists_rank_delta | trend_prefix }} {{ p.player_name }}</span>
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

  <!-- La Dupla -->
  <div class="section">
    <div class="section-title" style="color:#06d6a0;">🤝 La Dupla</div>
    <div class="section-body" style="border-left-color:#06d6a0;">
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

  <!-- Dúo Ganador -->
  <div class="section" style="margin-bottom:0;">
    <div class="section-title" style="color:#ffd166;">🏅 Dúo Ganador</div>
    <div class="section-body" style="border-left-color:#ffd166;">
      {% for wp in winning_pairs %}
      <div class="bar-row-wide">
        <span class="bar-name-wide">{{ wp.player_a_name }} + {{ wp.player_b_name }}</span>
        <div class="bar-track">
          <div class="bar winning" style="width:{{ (wp.count / max_winning * 100) | int }}%;"></div>
        </div>
        <span class="bar-value">{{ wp.count }}</span>
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

- [ ] **Step 2: Update unit test CSS anchor strings for new colors**

In `tests/unit/infrastructure/test_stats_renderer.py`, update the three tests in `TestBuildHtml` that depend on CSS/text anchors:

```python
def test_player_with_zero_goals_excluded_from_goals_section(self):
    """A player with 0 goals does not appear in the goals bar list."""
    alice = _make_player("a", "Alice", goals=3, assists=1, wins=2, draws=0, losses=1)
    bob = _make_player("b", "Bob", goals=0, assists=2, wins=1, draws=0, losses=2)
    html = self._build([alice, bob])
    goals_col_start = html.index('background:#f72585;"></span>Goles')
    assists_col_start = html.index('background:#3a86ff;"></span>Asistencias')
    goals_section = html[goals_col_start:assists_col_start]
    assert "Bob" not in goals_section

def test_player_with_zero_assists_excluded_from_assists_section(self):
    """A player with 0 assists does not appear in the assists bar list."""
    alice = _make_player("a", "Alice", goals=3, assists=0, wins=2, draws=0, losses=1)
    bob = _make_player("b", "Bob", goals=1, assists=2, wins=1, draws=0, losses=2)
    html = self._build([alice, bob])
    assists_col_start = html.index('background:#3a86ff;"></span>Asistencias')
    dupla_start = html.index("La Dupla")
    assists_section = html[assists_col_start:dupla_start]
    assert "Alice" not in assists_section

def test_player_with_zero_points_excluded_from_classification(self):
    """A player with 0 points does not appear in the classification table."""
    alice = _make_player("a", "Alice", goals=1, assists=0, wins=0, draws=0, losses=3)
    bob = _make_player("b", "Bob", goals=2, assists=1, wins=2, draws=0, losses=1)
    html = self._build([alice, bob])
    clasificacion_start = html.index("Clasificación</div>")
    split_cols_start = html.index('class="split-cols"')
    classification_section = html[clasificacion_start:split_cols_start]
    assert "Alice" not in classification_section

def test_player_with_goals_appears_in_goals_section(self):
    """A player with goals appears in the goals section."""
    alice = _make_player("a", "Alice", goals=5, assists=2, wins=3, draws=0, losses=0)
    html = self._build([alice])
    goals_col_start = html.index('background:#f72585;"></span>Goles')
    assists_col_start = html.index('background:#3a86ff;"></span>Asistencias')
    goals_section = html[goals_col_start:assists_col_start]
    assert "Alice" in goals_section
```

- [ ] **Step 3: Run all renderer unit tests**

```bash
nox -e test -- tests/unit/infrastructure/test_stats_renderer.py -v
```

Expected: all pass.

- [ ] **Step 4: Run integration renderer tests to verify PNG still generates**

```bash
nox -e test -- tests/integration/test_stats_renderer.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyball/infrastructure/images/stats_template.html \
        tests/unit/infrastructure/test_stats_renderer.py
git commit -m "feat(template): neon redesign, rename La Dupla, add Dúo Ganador section"
```

---

## Task 4: Update _post_match_stats to send one photo

**Files:**
- Modify: `pyball/infrastructure/http/app.py`

- [ ] **Step 1: Update _post_match_stats**

In `pyball/infrastructure/http/app.py`, replace `_post_match_stats`:

```python
async def _post_match_stats(
    bot: "telegram.Bot",
    container: "Container",
    settings: "Settings",
) -> None:
    """Compute and post the season stats image to the regulars stats topic.

    Runs as a background asyncio task. Errors are logged and swallowed so
    they never affect the match-finish response.

    Args:
        bot: Telegram Bot instance for sending photos.
        container: DI container with repositories.
        settings: Application settings for chat/thread IDs.
    """
    try:
        report = ComputeStats(container.meetup_repository, container.player_repository).execute()
        season_png = await StatsHtmlRenderer().render(report, scope="season")

        stats_thread_id = settings.telegram.regulars.stats_thread_id or None
        chat_id = settings.telegram.regulars.chat_id

        await bot.send_photo(
            chat_id=chat_id,
            photo=season_png,
            caption="📊 Esta temporada",
            message_thread_id=int(stats_thread_id) if stats_thread_id else None,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error posting match stats")
```

- [ ] **Step 2: Run the full test suite**

```bash
nox -e test
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add pyball/infrastructure/http/app.py
git commit -m "feat(http): post only season stats image after match finish"
```

---

## Task 5: Add /stats command handler (TDD)

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`
- Modify: `tests/integration/bot/test_meetup_handlers.py`

- [ ] **Step 1: Write failing tests for stats_handler**

Add at the bottom of `tests/integration/bot/test_meetup_handlers.py`:

```python
from pyball.bot.handlers.meetup import stats_handler
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer


@pytest.mark.asyncio
async def test_stats_handler_temporada_sends_photo(bot_update, bot_context, monkeypatch):
    """stats_handler with 'temporada' sends one photo with season caption."""
    fake_png = b"\x89PNG\r\n\x1a\n"
    captured = {}

    async def fake_render(self, report, scope="season"):
        captured["scope"] = scope
        return fake_png

    monkeypatch.setattr(StatsHtmlRenderer, "render", fake_render)
    bot_context.args = ["temporada"]
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_photo.assert_called_once()
    assert captured["scope"] == "season"
    kwargs = bot_update.message.reply_photo.call_args.kwargs
    assert kwargs["photo"] == fake_png
    assert "temporada" in kwargs["caption"].lower() or "Esta temporada" in kwargs["caption"]


@pytest.mark.asyncio
async def test_stats_handler_historico_sends_photo(bot_update, bot_context, monkeypatch):
    """stats_handler with 'historico' sends one photo with all-time caption."""
    fake_png = b"\x89PNG\r\n\x1a\n"
    captured = {}

    async def fake_render(self, report, scope="season"):
        captured["scope"] = scope
        return fake_png

    monkeypatch.setattr(StatsHtmlRenderer, "render", fake_render)
    bot_context.args = ["historico"]
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_photo.assert_called_once()
    assert captured["scope"] == "alltime"
    kwargs = bot_update.message.reply_photo.call_args.kwargs
    assert "Histórico" in kwargs["caption"]


@pytest.mark.asyncio
async def test_stats_handler_no_args_replies_help(bot_update, bot_context):
    """stats_handler with no args replies with a help message."""
    bot_context.args = []
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_text.assert_called_once()
    text = bot_update.message.reply_text.call_args.args[0]
    assert "temporada" in text and "historico" in text


@pytest.mark.asyncio
async def test_stats_handler_bad_arg_replies_help(bot_update, bot_context):
    """stats_handler with an unknown arg replies with a help message."""
    bot_context.args = ["unknown"]
    await stats_handler(bot_update, bot_context)
    bot_update.message.reply_text.assert_called_once()
    text = bot_update.message.reply_text.call_args.args[0]
    assert "temporada" in text and "historico" in text
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
nox -e test -- tests/integration/bot/test_meetup_handlers.py::test_stats_handler_temporada_sends_photo -v
```

Expected: `ImportError: cannot import name 'stats_handler'`.

- [ ] **Step 3: Add stats_handler and register it**

Add these imports at the top of `pyball/bot/handlers/meetup.py` (after existing imports):

```python
from pyball.application.meetup.compute_stats import ComputeStats
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
```

Add the handler function before `setup_meetup_handlers`:

```python
@authorized
async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command — send a stats image for the requested scope."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or args[0] not in ("temporada", "historico"):
        await message.reply_text("Usa /stats temporada o /stats historico")
        return

    scope = "season" if args[0] == "temporada" else "alltime"
    container: Container = context.bot_data["container"]
    caption = "📊 Esta temporada" if scope == "season" else "📊 Histórico"

    try:
        report = ComputeStats(
            container.meetup_repository, container.player_repository
        ).execute()
        png = await StatsHtmlRenderer().render(report, scope=scope)
        await message.reply_photo(photo=png, caption=caption)
    except Exception as error:
        logger.exception("Error sending stats: %s", error)
        await message.reply_text("Error al generar las estadísticas.")
```

Register it in `setup_meetup_handlers`:

```python
def setup_meetup_handlers(application):
    """Register meetup-related handlers."""
    application.add_handler(CommandHandler("new_meetup", new_meetup_handler))
    application.add_handler(CommandHandler("next_meetup", next_meetup_handler))
    application.add_handler(CommandHandler("add_player", add_player_handler))
    application.add_handler(CommandHandler("remove_player", remove_player_handler))
    application.add_handler(CommandHandler("create_teams", create_teams_handler))
    application.add_handler(CommandHandler("list_meetups", list_meetups_handler))
    application.add_handler(CommandHandler("show_meetup", show_meetup_handler))
    application.add_handler(CommandHandler("search", search_handler))
    application.add_handler(CommandHandler("start_match", start_match_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
```

- [ ] **Step 4: Run all stats handler tests**

```bash
nox -e test -- tests/integration/bot/test_meetup_handlers.py -k stats -v
```

Expected: all 4 new tests pass.

- [ ] **Step 5: Run full test suite and linter**

```bash
nox -e test
nox -e lint
```

Expected: all pass, pylint 10.00/10.

- [ ] **Step 6: Commit**

```bash
git add pyball/bot/handlers/meetup.py \
        tests/integration/bot/test_meetup_handlers.py
git commit -m "feat(bot): add /stats [temporada|historico] admin command"
```
