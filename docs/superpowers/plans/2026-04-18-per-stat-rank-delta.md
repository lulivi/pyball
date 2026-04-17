# Per-Stat Rank Delta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `rank_delta` field on `PlayerStats` with three independent delta fields
(`points_rank_delta`, `goals_rank_delta`, `assists_rank_delta`) so each section of the stats image
shows movement arrows relative to its own ranking, and players with 0 in a stat are excluded from
that section.

**Architecture:** `PlayerStats` gains three delta fields; `_build_scoped_report` computes each
independently (ranking only players with stat > 0); the Jinja2 `trend_prefix` filter takes
`int | None` directly; the template picks the right field per section. `None` renders as `▲`
(new entrant); `★` is removed entirely.

**Tech Stack:** Python dataclasses, pytest, Jinja2, Playwright (integration tests only)

---

## File Map

| File | Change |
|---|---|
| `pyball/application/meetup/compute_stats.py` | Replace `rank_delta` with 3 fields; compute all 3 deltas |
| `pyball/infrastructure/images/stats_renderer.py` | `_trend_prefix(int\|None)`, filter 0-stat players in `_build_html` |
| `pyball/infrastructure/images/stats_template.html` | Use per-field delta; remove `trend-new` CSS |
| `tests/unit/application/test_compute_stats.py` | Update existing + add new delta tests |
| `tests/unit/infrastructure/test_stats_renderer.py` | New — unit tests for `_build_html` and `_trend_prefix` |
| `tests/integration/test_stats_renderer.py` | Update fixtures to use 3 delta fields |

---

## Task 1: Replace `rank_delta` with three delta fields in `PlayerStats`

**Files:**
- Modify: `pyball/application/meetup/compute_stats.py`
- Modify: `tests/unit/application/test_compute_stats.py`
- Modify: `tests/integration/test_stats_renderer.py`

- [ ] **Step 1: Write a failing test that accesses `points_rank_delta`**

Add this test to `tests/unit/application/test_compute_stats.py` inside `TestComputeStatsRankDelta`:

```python
def test_points_rank_delta_field_exists(self):
    """PlayerStats has points_rank_delta instead of rank_delta."""
    alice = make_player("Alice")
    bob = make_player("Bob")
    meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
    report = ComputeStats(meetup_repo, player_repo).execute()
    alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
    assert hasattr(alice_stats, "points_rank_delta")
    assert hasattr(alice_stats, "goals_rank_delta")
    assert hasattr(alice_stats, "assists_rank_delta")
    assert not hasattr(alice_stats, "rank_delta")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/llv/g/b/pyball
poetry run pytest tests/unit/application/test_compute_stats.py::TestComputeStatsRankDelta::test_points_rank_delta_field_exists -v
```

Expected: FAIL — `assert not hasattr(alice_stats, 'rank_delta')` fails (field still exists).

- [ ] **Step 3: Replace `rank_delta` with three fields in `PlayerStats`**

In `pyball/application/meetup/compute_stats.py`, replace:

```python
    rank_delta: int | None
```

with:

```python
    points_rank_delta: int | None
    goals_rank_delta: int | None
    assists_rank_delta: int | None
```

- [ ] **Step 4: Update the `PlayerStats` constructor call in `_build_scoped_report`**

In `pyball/application/meetup/compute_stats.py`, replace:

```python
        PlayerStats(
            player_id=pid,
            player_name=player_names.get(pid, pid),
            goals=d["goals"],
            assists=d["assists"],
            matches_played=d["mp"],
            wins=d["w"],
            draws=d["d"],
            losses=d["l"],
            rank_delta=None,
        )
```

with:

```python
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
```

- [ ] **Step 5: Update the delta assignment in `_build_scoped_report`**

In `pyball/application/meetup/compute_stats.py`, replace the entire `if prev_meetups is not None:` block:

```python
    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups)
        prev_ranked = sorted(
            prev_data.keys(),
            key=lambda pid: _points_from_counters(prev_data[pid]),
            reverse=True,
        )
        prev_rank = {pid: i + 1 for i, pid in enumerate(prev_ranked)}
        for i, player in enumerate(stats_list):
            current_pos = i + 1
            if player.player_id in prev_rank:
                player.rank_delta = prev_rank[player.player_id] - current_pos
```

with a placeholder that preserves the structure (per-stat computation comes in Task 2):

```python
    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups)
        prev_pts_ranked = sorted(
            [pid for pid in prev_data if _points_from_counters(prev_data[pid]) > 0],
            key=lambda pid: _points_from_counters(prev_data[pid]),
            reverse=True,
        )
        prev_pts_rank = {pid: i + 1 for i, pid in enumerate(prev_pts_ranked)}
        current_pts = [p for p in stats_list if p.points > 0]
        for i, player in enumerate(current_pts):
            if player.player_id in prev_pts_rank:
                player.points_rank_delta = prev_pts_rank[player.player_id] - (i + 1)
```

(goals and assists deltas will be added in Task 2)

- [ ] **Step 6: Update existing `TestComputeStatsRankDelta` tests to use `points_rank_delta`**

In `tests/unit/application/test_compute_stats.py`, rename all occurrences of `rank_delta` to `points_rank_delta` inside `TestComputeStatsRankDelta`. The exact replacements:

- `assert p.rank_delta is None` → `assert p.points_rank_delta is None`
- `assert alice_stats.rank_delta == 0` → `assert alice_stats.points_rank_delta == 0`
- `assert alice_stats.rank_delta == 1` → `assert alice_stats.points_rank_delta == 1`
- `assert alice_stats.rank_delta is not None` → `assert alice_stats.points_rank_delta is not None`
- `assert alice_stats.rank_delta < 0` → `assert alice_stats.points_rank_delta < 0`
- `assert charlie_stats.rank_delta is None` → `assert charlie_stats.points_rank_delta is None`

Also remove the `test_points_rank_delta_field_exists` test you added in Step 1 (the field now exists, the existing tests already cover behavior).

- [ ] **Step 7: Update integration test fixtures**

In `tests/integration/test_stats_renderer.py`, replace `_make_full_report`:

```python
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
```

And replace the `PlayerStats` constructor calls in `test_season_and_alltime_images_differ`:

```python
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
```

- [ ] **Step 8: Run all tests to verify nothing is broken**

```bash
poetry run pytest tests/unit/application/test_compute_stats.py tests/integration/test_stats_renderer.py -v
```

Expected: all pass (the renderer still reads `player.rank_delta` in the Jinja2 filter — it will error on `AttributeError`; if it does, note it but the unit tests for compute_stats should pass since they don't invoke the renderer).

Actually the renderer uses `p | trend_prefix` in the template which calls `_trend_prefix(player)` → `delta = player.rank_delta`. This will raise `AttributeError`. The integration tests that call `render()` will fail. That's acceptable — they will be fixed in Task 3.

Run only unit tests for now:

```bash
poetry run pytest tests/unit/application/test_compute_stats.py -v
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add pyball/application/meetup/compute_stats.py \
        tests/unit/application/test_compute_stats.py \
        tests/integration/test_stats_renderer.py
git commit -m "refactor(stats): replace rank_delta with points/goals/assists_rank_delta fields"
```

---

## Task 2: Compute `goals_rank_delta` and `assists_rank_delta` in `_build_scoped_report`

**Files:**
- Modify: `pyball/application/meetup/compute_stats.py`
- Modify: `tests/unit/application/test_compute_stats.py`

- [ ] **Step 1: Write failing tests for goals and assists deltas**

Add these four tests to `TestComputeStatsRankDelta` in `tests/unit/application/test_compute_stats.py`:

```python
def test_goals_rank_delta_none_when_player_had_no_previous_goals(self):
    """A player with 0 goals in the previous ranking gets goals_rank_delta=None."""
    alice = make_player("Alice")
    bob = make_player("Bob")
    event = GoalEvent(
        scorer_id=alice.id,
        assistant_id=None,
        team="A",
        timestamp=datetime(2026, 1, 17, 20, 5),
    )
    meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup2 = make_meetup(
        datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0, [event]
    )
    meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
    report = ComputeStats(meetup_repo, player_repo).execute()
    alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
    assert alice_stats.goals_rank_delta is None

def test_assists_rank_delta_none_when_player_had_no_previous_assists(self):
    """A player with 0 assists previously gets assists_rank_delta=None."""
    alice = make_player("Alice")
    bob = make_player("Bob")
    event = GoalEvent(
        scorer_id=alice.id,
        assistant_id=bob.id,
        team="A",
        timestamp=datetime(2026, 1, 17, 20, 5),
    )
    meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup2 = make_meetup(
        datetime(2026, 1, 17, 20, 0), [alice.id, bob.id], [alice.id], 1, 0, [event]
    )
    meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
    report = ComputeStats(meetup_repo, player_repo).execute()
    bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
    assert bob_stats.assists_rank_delta is None

def test_goals_rank_delta_independent_from_points_rank(self):
    """goals_rank_delta reflects the goals ranking, not the points ranking."""
    alice = make_player("Alice")
    bob = make_player("Bob")
    # meetup1: Bob wins and scores 2 goals → Bob 1st in goals, 1st in points
    event_b1 = GoalEvent(
        scorer_id=bob.id, assistant_id=None, team="B",
        timestamp=datetime(2026, 1, 10, 20, 5),
    )
    event_b2 = GoalEvent(
        scorer_id=bob.id, assistant_id=None, team="B",
        timestamp=datetime(2026, 1, 10, 20, 10),
    )
    meetup1 = make_meetup(
        datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 2, [event_b1, event_b2]
    )
    # meetup2: Alice wins and scores 3 goals → Alice moves to 1st in goals
    event_a1 = GoalEvent(
        scorer_id=alice.id, assistant_id=None, team="A",
        timestamp=datetime(2026, 1, 17, 20, 5),
    )
    event_a2 = GoalEvent(
        scorer_id=alice.id, assistant_id=None, team="A",
        timestamp=datetime(2026, 1, 17, 20, 10),
    )
    event_a3 = GoalEvent(
        scorer_id=alice.id, assistant_id=None, team="A",
        timestamp=datetime(2026, 1, 17, 20, 15),
    )
    meetup2 = make_meetup(
        datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 3, 0,
        [event_a1, event_a2, event_a3],
    )
    meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
    report = ComputeStats(meetup_repo, player_repo).execute()
    alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
    # Alice was 2nd in goals (prev), now 1st → delta = 2 - 1 = +1
    assert alice_stats.goals_rank_delta == 1

def test_zero_points_player_has_none_points_rank_delta(self):
    """A player with 0 points is excluded from the points ranking, so delta is None."""
    alice = make_player("Alice")
    bob = make_player("Bob")
    meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
    meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
    report = ComputeStats(meetup_repo, player_repo).execute()
    bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
    # Bob has 0 points in both rankings → not ranked → delta None
    assert bob_stats.points_rank_delta is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/application/test_compute_stats.py::TestComputeStatsRankDelta -v -k "goals_rank_delta or assists_rank_delta or zero_points"
```

Expected: all 4 new tests FAIL (goals_rank_delta and assists_rank_delta are always `None`).

- [ ] **Step 3: Add goals and assists delta computation to `_build_scoped_report`**

In `pyball/application/meetup/compute_stats.py`, extend the `if prev_meetups is not None:` block. Replace the entire block:

```python
    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups)
        prev_pts_ranked = sorted(
            [pid for pid in prev_data if _points_from_counters(prev_data[pid]) > 0],
            key=lambda pid: _points_from_counters(prev_data[pid]),
            reverse=True,
        )
        prev_pts_rank = {pid: i + 1 for i, pid in enumerate(prev_pts_ranked)}
        current_pts = [p for p in stats_list if p.points > 0]
        for i, player in enumerate(current_pts):
            if player.player_id in prev_pts_rank:
                player.points_rank_delta = prev_pts_rank[player.player_id] - (i + 1)
```

with:

```python
    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups)

        prev_pts_ranked = sorted(
            [pid for pid in prev_data if _points_from_counters(prev_data[pid]) > 0],
            key=lambda pid: _points_from_counters(prev_data[pid]),
            reverse=True,
        )
        prev_pts_rank = {pid: i + 1 for i, pid in enumerate(prev_pts_ranked)}
        for i, player in enumerate([p for p in stats_list if p.points > 0]):
            if player.player_id in prev_pts_rank:
                player.points_rank_delta = prev_pts_rank[player.player_id] - (i + 1)

        prev_goals_ranked = sorted(
            [pid for pid in prev_data if prev_data[pid]["goals"] > 0],
            key=lambda pid: prev_data[pid]["goals"],
            reverse=True,
        )
        prev_goals_rank = {pid: i + 1 for i, pid in enumerate(prev_goals_ranked)}
        current_goals = sorted(
            [p for p in stats_list if p.goals > 0],
            key=lambda p: p.goals,
            reverse=True,
        )
        for i, player in enumerate(current_goals):
            if player.player_id in prev_goals_rank:
                player.goals_rank_delta = prev_goals_rank[player.player_id] - (i + 1)

        prev_assists_ranked = sorted(
            [pid for pid in prev_data if prev_data[pid]["assists"] > 0],
            key=lambda pid: prev_data[pid]["assists"],
            reverse=True,
        )
        prev_assists_rank = {pid: i + 1 for i, pid in enumerate(prev_assists_ranked)}
        current_assists = sorted(
            [p for p in stats_list if p.assists > 0],
            key=lambda p: p.assists,
            reverse=True,
        )
        for i, player in enumerate(current_assists):
            if player.player_id in prev_assists_rank:
                player.assists_rank_delta = prev_assists_rank[player.player_id] - (i + 1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/unit/application/test_compute_stats.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/compute_stats.py \
        tests/unit/application/test_compute_stats.py
git commit -m "feat(stats): compute per-stat rank deltas for points, goals, and assists"
```

---

## Task 3: Update renderer — `_trend_prefix` signature and `_build_html` zero-stat filtering

**Files:**
- Modify: `pyball/infrastructure/images/stats_renderer.py`
- Create: `tests/unit/infrastructure/test_stats_renderer.py`

- [ ] **Step 1: Write failing unit tests for `_trend_prefix` and `_build_html`**

Create `tests/unit/infrastructure/test_stats_renderer.py`:

```python
"""Unit tests for StatsHtmlRenderer._build_html and _trend_prefix."""

import pytest

from markupsafe import Markup

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    PlayerStats,
    StatsScopedReport,
)
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer, _trend_prefix


def _make_player(
    player_id: str,
    name: str,
    goals: int,
    assists: int,
    wins: int,
    draws: int,
    losses: int,
    points_rank_delta: int | None = 0,
    goals_rank_delta: int | None = 0,
    assists_rank_delta: int | None = 0,
) -> PlayerStats:
    return PlayerStats(
        player_id=player_id,
        player_name=name,
        goals=goals,
        assists=assists,
        matches_played=wins + draws + losses,
        wins=wins,
        draws=draws,
        losses=losses,
        points_rank_delta=points_rank_delta,
        goals_rank_delta=goals_rank_delta,
        assists_rank_delta=assists_rank_delta,
    )


class TestTrendPrefix:
    """Unit tests for the _trend_prefix Jinja2 filter."""

    def test_none_delta_returns_trend_up(self):
        """None delta (new entrant) renders as ▲."""
        result = _trend_prefix(None)
        assert "trend-up" in result
        assert "▲" in result

    def test_positive_delta_returns_trend_up(self):
        """Positive delta (moved up) renders as ▲."""
        result = _trend_prefix(1)
        assert "trend-up" in result

    def test_negative_delta_returns_trend_down(self):
        """Negative delta (dropped) renders as ▼."""
        result = _trend_prefix(-1)
        assert "trend-down" in result
        assert "▼" in result

    def test_zero_delta_returns_trend_same(self):
        """Zero delta (unchanged) renders as ─."""
        result = _trend_prefix(0)
        assert "trend-same" in result
        assert "─" in result

    def test_no_star_symbol(self):
        """★ symbol is never returned."""
        for delta in [None, 0, 1, -1, 5, -5]:
            assert "★" not in _trend_prefix(delta)


class TestBuildHtml:
    """Unit tests for StatsHtmlRenderer._build_html zero-stat filtering."""

    def _build(self, players, chemistry=None) -> str:
        scoped = StatsScopedReport(
            players=sorted(players, key=lambda p: p.points, reverse=True),
            chemistry=chemistry or [],
        )
        return StatsHtmlRenderer()._build_html(scoped, "Test")

    def test_player_with_zero_goals_excluded_from_goals_section(self):
        """A player with 0 goals does not appear in the goals bar list."""
        alice = _make_player("a", "Alice", goals=3, assists=1, wins=2, draws=0, losses=1)
        bob = _make_player("b", "Bob", goals=0, assists=2, wins=1, draws=0, losses=2)
        html = self._build([alice, bob])
        # Bob should not appear next to a goals bar
        goals_section_start = html.index("Goles")
        asistencias_start = html.index("Asistencias")
        goals_section = html[goals_section_start:asistencias_start]
        assert "Bob" not in goals_section

    def test_player_with_zero_assists_excluded_from_assists_section(self):
        """A player with 0 assists does not appear in the assists bar list."""
        alice = _make_player("a", "Alice", goals=3, assists=0, wins=2, draws=0, losses=1)
        bob = _make_player("b", "Bob", goals=1, assists=2, wins=1, draws=0, losses=2)
        html = self._build([alice, bob])
        asistencias_start = html.index("Asistencias")
        parejas_start = html.index("Parejas")
        assists_section = html[asistencias_start:parejas_start]
        assert "Alice" not in assists_section

    def test_player_with_zero_points_excluded_from_classification(self):
        """A player with 0 points does not appear in the classification table."""
        alice = _make_player("a", "Alice", goals=1, assists=0, wins=0, draws=0, losses=3)
        bob = _make_player("b", "Bob", goals=2, assists=1, wins=2, draws=0, losses=1)
        html = self._build([alice, bob])
        clasificacion_start = html.index("Clasificación")
        goles_start = html.index("Goles")
        classification_section = html[clasificacion_start:goles_start]
        assert "Alice" not in classification_section

    def test_player_with_stats_appears_in_correct_section(self):
        """A player with goals appears in the goals section."""
        alice = _make_player("a", "Alice", goals=5, assists=2, wins=3, draws=0, losses=0)
        html = self._build([alice])
        goals_section_start = html.index("Goles")
        asistencias_start = html.index("Asistencias")
        goals_section = html[goals_section_start:asistencias_start]
        assert "Alice" in goals_section
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/infrastructure/test_stats_renderer.py -v
```

Expected: `TestTrendPrefix` tests fail because `_trend_prefix` currently takes a `PlayerStats` not an `int | None`; `TestBuildHtml` tests fail because filtering is not yet implemented.

- [ ] **Step 3: Update `_trend_prefix` to accept `int | None`**

In `pyball/infrastructure/images/stats_renderer.py`, replace the entire `_trend_prefix` function:

```python
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
```

- [ ] **Step 4: Update `_build_html` to filter zero-stat players**

In `pyball/infrastructure/images/stats_renderer.py`, replace these three lines in `_build_html`:

```python
        players = scoped.players[:10]
        players_by_goals = sorted(scoped.players, key=lambda p: p.goals, reverse=True)[:10]
        players_by_assists = sorted(scoped.players, key=lambda p: p.assists, reverse=True)[:10]
```

with:

```python
        players = [p for p in scoped.players if p.points > 0][:10]
        players_by_goals = sorted(
            [p for p in scoped.players if p.goals > 0],
            key=lambda p: p.goals,
            reverse=True,
        )[:10]
        players_by_assists = sorted(
            [p for p in scoped.players if p.assists > 0],
            key=lambda p: p.assists,
            reverse=True,
        )[:10]
```

Note: `scoped.players` is already sorted by points descending (from `_build_scoped_report`), so filtering preserves the correct classification order.

- [ ] **Step 5: Run unit tests to verify they pass**

```bash
poetry run pytest tests/unit/infrastructure/test_stats_renderer.py -v
```

Expected: all pass.

- [ ] **Step 6: Run full unit test suite to check for regressions**

```bash
poetry run pytest tests/unit/ -v
```

Expected: all pass. (Integration tests are skipped here — they will be fixed in Task 4.)

- [ ] **Step 7: Commit**

```bash
git add pyball/infrastructure/images/stats_renderer.py \
        tests/unit/infrastructure/test_stats_renderer.py
git commit -m "feat(renderer): per-stat trend arrows, filter zero-stat players, remove star indicator"
```

---

## Task 4: Update the Jinja2 template and fix integration tests

**Files:**
- Modify: `pyball/infrastructure/images/stats_template.html`
- Modify: `tests/integration/test_stats_renderer.py`

- [ ] **Step 1: Update the template to use per-field delta and remove `trend-new`**

In `pyball/infrastructure/images/stats_template.html`:

**a) Remove the `.trend-new` CSS rule.** Delete this line from the `<style>` block:

```css
.trend-new { color: #f0c040; }
```

**b) In the Clasificación `<tbody>`, change the player name cell** from:

```html
            <td>{{ p | trend_prefix }} {{ p.player_name }}</td>
```

to:

```html
            <td>{{ p.points_rank_delta | trend_prefix }} {{ p.player_name }}</td>
```

**c) In the Goles section, change the bar-name span** from:

```html
            <span class="bar-name">{{ p | trend_prefix }} {{ p.player_name }}</span>
```

to:

```html
            <span class="bar-name">{{ p.goals_rank_delta | trend_prefix }} {{ p.player_name }}</span>
```

**d) In the Asistencias section, change the bar-name span** from:

```html
            <span class="bar-name">{{ p | trend_prefix }} {{ p.player_name }}</span>
```

to:

```html
            <span class="bar-name">{{ p.assists_rank_delta | trend_prefix }} {{ p.player_name }}</span>
```

- [ ] **Step 2: Run integration tests**

```bash
poetry run pytest tests/integration/test_stats_renderer.py -v
```

Expected: all pass. The renderer now uses `p.points_rank_delta | trend_prefix`, `p.goals_rank_delta | trend_prefix`, `p.assists_rank_delta | trend_prefix` — all valid `int | None` values.

- [ ] **Step 3: Add an integration test that verifies `★` never appears in the output**

Add this test to `TestStatsHtmlRenderer` in `tests/integration/test_stats_renderer.py`. First add `import re` at the top of the file, then add the test:

```python
    @pytest.mark.asyncio
    async def test_no_star_symbol_in_output(self):
        """The ★ indicator is never shown regardless of player data."""
        report = _make_full_report()
        season_png, _ = await StatsHtmlRenderer().render(report)
        # We test via HTML rather than PNG — call _build_html directly
        scoped = report.season
        html = StatsHtmlRenderer()._build_html(scoped, "Test")
        assert "★" not in html
```

- [ ] **Step 4: Run integration tests again**

```bash
poetry run pytest tests/integration/test_stats_renderer.py -v
```

Expected: all pass including the new `test_no_star_symbol_in_output`.

- [ ] **Step 5: Run the full test suite and linter**

```bash
poetry run pytest tests/ -v
make lint
```

Expected: all tests pass, pylint score 10.00/10.

- [ ] **Step 6: Commit**

```bash
git add pyball/infrastructure/images/stats_template.html \
        tests/integration/test_stats_renderer.py
git commit -m "feat(template): use per-stat rank delta arrows, remove star indicator"
```
