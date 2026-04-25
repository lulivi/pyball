# Legacy Assists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the system to use historical assist counts from the legacy SQLite database for team balancing and statistics, without modifying the DDD model with guessed data.

**Architecture:** Keep legacy data in a separate JSON file (`data/legacy_stats.json`) and load it as a read-only reference. The `LegacyStats` class aggregates this data and provides a simple interface for balance.py and compute_stats.py to consume.

**Tech Stack:** Python, JSON persistence, existing DDD architecture

---

### Task 1: Create LegacyStats class

**Files:**
- Create: `pyball/infrastructure/persistence/legacy_stats.py`
- Modify: `pyball/infrastructure/persistence/__init__.py`
- Test: `tests/unit/infrastructure/test_legacy_stats.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/infrastructure/test_legacy_stats.py
import pytest
from pyball.infrastructure.persistence.legacy_stats import LegacyStats


def test_get_assists_returns_correct_value():
    data = {
        "players": {
            "uuid-1": {"goals": 10, "assists": 5, "matches": 15},
            "uuid-2": {"goals": 3, "assists": 8, "matches": 20},
        }
    }
    stats = LegacyStats(data)
    assert stats.get_assists("uuid-1") == 5
    assert stats.get_assists("uuid-2") == 8
    assert stats.get_assists("unknown") == 0


def test_get_goals_returns_correct_value():
    data = {
        "players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}
    }
    stats = LegacyStats(data)
    assert stats.get_goals("uuid-1") == 10
    assert stats.get_goals("unknown") == 0


def test_get_matches_returns_correct_value():
    data = {
        "players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}
    }
    stats = LegacyStats(data)
    assert stats.get_matches("uuid-1") == 15
    assert stats.get_matches("unknown") == 0


def test_get_returns_full_dict():
    data = {
        "players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}
    }
    stats = LegacyStats(data)
    assert stats.get("uuid-1") == {"goals": 10, "assists": 5, "matches": 15}
    assert stats.get("unknown") == {"goals": 0, "assists": 0, "matches": 0}


def test_all_players_returns_list():
    data = {
        "players": {
            "uuid-1": {"goals": 10, "assists": 5, "matches": 15},
            "uuid-2": {"goals": 3, "assists": 8, "matches": 20},
        }
    }
    stats = LegacyStats(data)
    assert sorted(stats.all_players()) == ["uuid-1", "uuid-2"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/unit/infrastructure/test_legacy_stats.py -v
```
Expected: FAIL with "module 'pyball.infrastructure.persistence.legacy_stats' not found"

- [ ] **Step 3: Write minimal implementation**

```python
# pyball/infrastructure/persistence/legacy_stats.py
"""Legacy statistics loader for historical assist data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LegacyStats:
    """Read-only access to legacy aggregate statistics."""

    _data: dict[str, dict[str, int]]

    def get(self, player_id: str) -> dict[str, int]:
        """Return {goals, assists, matches} for player_id, or zeros if not found."""
        if player_id in self._data.get("players", {}):
            return self._data["players"][player_id]
        return {"goals": 0, "assists": 0, "matches": 0}

    def get_assists(self, player_id: str) -> int:
        """Return total assists for player_id."""
        return self.get(player_id).get("assists", 0)

    def get_goals(self, player_id: str) -> int:
        """Return total goals for player_id."""
        return self.get(player_id).get("goals", 0)

    def get_matches(self, player_id: str) -> int:
        """Return total matches for player_id."""
        return self.get(player_id).get("matches", 0)

    def all_players(self) -> list[str]:
        """Return list of all player IDs in legacy stats."""
        return list(self._data.get("players", {}).keys())

    @classmethod
    def from_file(cls, path: str) -> LegacyStats:
        """Load legacy stats from a JSON file."""
        import json
        from pathlib import Path

        if not Path(path).exists():
            return cls({"players": {}})
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)
```

- [ ] **Step 4: Update __init__.py**

```python
# pyball/infrastructure/persistence/__init__.py
from pyball.infrastructure.persistence.legacy_stats import LegacyStats

__all__ = ["JsonMeetupRepository", "JsonPlayerRepository", "LegacyStats"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/unit/infrastructure/test_legacy_stats.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/infrastructure/persistence/legacy_stats.py pyball/infrastructure/persistence/__init__.py tests/unit/infrastructure/test_legacy_stats.py && git commit -m "feat: add LegacyStats class for reading legacy assist data"
```

---

### Task 2: Integrate LegacyStats into Container

**Files:**
- Modify: `pyball/application/container.py`
- Test: Verify existing tests still pass

- [ ] **Step 1: Modify container.py**

Add `LegacyStats` import and property to Container:

```python
# pyball/application/container.py - add import
from pyball.infrastructure.persistence import JsonMeetupRepository, JsonPlayerRepository, LegacyStats

# In Container class, add:
class Container:
    def __init__(self, data_dir: Path | None = None):
        # ... existing code ...
        self._legacy_stats: LegacyStats | None = None

    @property
    def legacy_stats(self) -> LegacyStats:
        """Get the legacy stats, loading from file if necessary."""
        if self._legacy_stats is None:
            legacy_path = self._data_dir / "legacy_stats.json"
            self._legacy_stats = LegacyStats.from_file(str(legacy_path))
        return self._legacy_stats
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/unit/application/ -v --tb=short 2>&1 | head -50
```
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/application/container.py && git commit -m "feat: add legacy_stats property to Container"
```

---

### Task 3: Integrate LegacyStats into balance.py

**Files:**
- Modify: `pyball/application/meetup/balance.py`
- Test: Existing tests in `tests/unit/application/test_balance.py`

- [ ] **Step 1: Modify balance.py to accept legacy_stats parameter**

Add parameter to `_player_stats` function (line 20):

```python
def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,  # NEW PARAMETER
) -> tuple[int, float, float, float]:
```

Update the function body to add legacy assists (after the existing assists loop, around line 43):

```python
    # After: for event in meetup.result.events:
    #           if event.assistant_id == player_id:
    #               assists += 1

    # Add legacy assists
    if legacy_stats and mp > 0:
        legacy = legacy_stats.get(str(player_id.value))
        assists += legacy["assists"]

    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp
```

- [ ] **Step 2: Update _player_role function**

Add `legacy_stats` parameter to `_player_role` (line 49) and pass it to `_count_events`:

```python
def _player_role(
    player_id: PlayerId,
    season_meetups: list[Meetup],
    all_meetups: list[Meetup] | None = None,
    legacy_stats: LegacyStats | None = None,  # NEW PARAMETER
) -> str:
```

Inside `_player_role`, update the calls to `_player_stats` (lines 111, 115):

```python
    mp_s, gpm_s, apm_s, wr_s = _player_stats(pid, season_meetups, legacy_stats)
    # ...
    mp_a, gpm_a, apm_a, wr_a = _player_stats(pid, all_meetups, legacy_stats)
```

- [ ] **Step 3: Update compute_player_scores function**

Find `compute_player_scores` function (line 99) and add `legacy_stats` parameter:

```python
def compute_player_scores(
    player_ids: list[PlayerId],
    meetups: list[Meetup],
    all_meetups: list[Meetup] | None = None,
    legacy_stats: LegacyStats | None = None,  # NEW PARAMETER
) -> list[tuple[PlayerId, float]]:
```

Pass `legacy_stats` to `_player_role` calls in this function.

- [ ] **Step 4: Run existing tests**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/unit/application/test_balance.py -v --tb=short
```
Expected: All tests pass (legacy_stats defaults to None, so existing behavior unchanged)

- [ ] **Step 5: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/application/meetup/balance.py && git commit -m "feat: add legacy_stats parameter to balance.py functions"
```

---

### Task 4: Integrate LegacyStats into compute_stats.py

**Files:**
- Modify: `pyball/application/meetup/compute_stats.py`
- Test: `tests/unit/application/test_compute_stats.py`

- [ ] **Step 1: Add import and modify _aggregate function**

Add import at top of file:

```python
from pyball.infrastructure.persistence import LegacyStats
```

Modify `_aggregate` function signature (line 87):

```python
def _aggregate(
    meetups: list,
    legacy_stats: LegacyStats | None = None,  # NEW PARAMETER
) -> tuple[dict[str, dict], dict[tuple[str, str], int], dict[tuple[str, str], int]]:
```

Add legacy assists after the events loop (after line 144):

```python
        # After: player_data[assistant_id]["assists"] += 1

    # Add legacy assists to all players in player_data
    if legacy_stats:
        for pid, data in player_data.items():
            legacy = legacy_stats.get(pid)
            data["assists"] += legacy.get("assists", 0)

    return player_data, chemistry_counts, winning_counts
```

- [ ] **Step 2: Update _build_scoped_report function**

Modify signature (line 149):

```python
def _build_scoped_report(
    meetups: list,
    player_names: dict[str, str],
    prev_meetups: list | None = None,
    legacy_stats: LegacyStats | None = None,  # NEW PARAMETER
) -> StatsScopedReport:
```

Pass legacy_stats to `_aggregate` calls (line 155 and line 176):

```python
    player_data, chemistry_counts, winning_counts = _aggregate(meetups, legacy_stats)
    # ...
    if prev_meetups is not None:
        prev_data, _, _ = _aggregate(prev_meetups, legacy_stats)
```

- [ ] **Step 3: Update ComputeStats class**

Find the `ComputeStats` class and update its methods to accept and pass `legacy_stats`.

Look for the class around line 220 and find methods that call `_build_scoped_report`.

- [ ] **Step 4: Run existing tests**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/unit/application/test_compute_stats.py -v --tb=short
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/application/meetup/compute_stats.py && git commit -m "feat: add legacy_stats parameter to compute_stats.py"
```

---

### Task 5: Update CreateTeams to pass LegacyStats

**Files:**
- Modify: `pyball/application/meetup/create_teams.py`
- Test: Existing integration

- [ ] **Step 1: Modify CreateTeams use case**

Check how CreateTeams calls `compute_player_scores` and ensure it passes `legacy_stats`:

```python
# In create_teams.py, update the CreateTeams class to accept legacy_stats
# and pass it to compute_player_scores
```

- [ ] **Step 2: Update Container.create_teams method**

Ensure the Container passes `legacy_stats` to `CreateTeams`:

```python
# In container.py, modify create_teams method
def create_teams(self) -> CreateTeams:
    return CreateTeams(self.meetup_repository, self.legacy_stats)
```

- [ ] **Step 3: Run tests**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/ -v --tb=short -k "team" 2>&1 | head -50
```

- [ ] **Step 4: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/application/meetup/create_teams.py pyball/application/container.py && git commit -m "feat: pass legacy_stats to CreateTeams"
```

---

### Task 6: Update finish_match to pass LegacyStats for stats

**Files:**
- Modify: `pyball/infrastructure/http/app.py` (the POST /api/match/finish endpoint)
- Test: Integration tests

- [ ] **Step 1: Pass legacy_stats to ComputeStats**

When the finish_match endpoint creates a `ComputeStats` instance, pass the `legacy_stats` from Container.

- [ ] **Step 2: Run tests**

```bash
cd /home/llv/g/b/pyball && uv run pytest tests/ -v --tb=short -k "finish" 2>&1 | head -30
```

- [ ] **Step 3: Commit**

```bash
cd /home/llv/g/b/pyball && git add pyball/infrastructure/http/app.py && git commit -m "feat: pass legacy_stats to ComputeStats in finish_match"
```

---

### Task 7: Update migration script to generate legacy_stats.json

**Files:**
- Modify: `scripts/migrate_legacy_sqlite_to_json.py`
- Test: Manual test with existing database

- [ ] **Step 1: Add function to generate legacy_stats.json**

In the migration script, after collecting match_statistic rows (line 88), aggregate by player:

```python
def _generate_legacy_stats(
    conn: sqlite3.Connection,
    old_id_to_uuid: dict[int, str],
    output_dir: Path,
) -> None:
    """Generate legacy_stats.json with aggregate goals/assists/matches per player."""
    cur = conn.execute(
        "SELECT player_id, team, goals, assists FROM match_statistic ORDER BY player_id"
    )
    rows = cur.fetchall()

    legacy: dict[str, dict[str, int]] = {"players": {}}

    for row in rows:
        player_uuid = old_id_to_uuid.get(row["player_id"])
        if player_uuid is None:
            continue

        if player_uuid not in legacy["players"]:
            legacy["players"][player_uuid] = {"goals": 0, "assists": 0, "matches": 0}

        legacy["players"][player_uuid]["goals"] += row["goals"]
        legacy["players"][player_uuid]["assists"] += row["assists"]
        legacy["players"][player_uuid]["matches"] += 1

    legacy_file = output_dir / "legacy_stats.json"
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(legacy, f, indent=2, ensure_ascii=False)

    print(f"  Legacy stats: {len(legacy['players'])} players written to {legacy_file}")
```

- [ ] **Step 2: Call the function in main()**

Add call after `_migrate_meetups`:

```python
    _generate_legacy_stats(conn, old_id_to_uuid, args.output_dir)
```

- [ ] **Step 3: Test migration script**

If you have a legacy database available, run:

```bash
cd /home/llv/g/b/pyball && python scripts/migrate_legacy_sqlite_to_json.py /path/to/legacy.db --output-dir data/
```

Verify `data/legacy_stats.json` is created with correct structure.

- [ ] **Step 4: Commit**

```bash
cd /home/llv/g/b/pyball && git add scripts/migrate_legacy_sqlite_to_json.py && git commit -m "feat: generate legacy_stats.json during migration"
```

---

### Task 8: Run full test suite and lint

**Files:**
- Test: Full test suite
- Lint: `make lint`

- [ ] **Step 1: Run full test suite**

```bash
cd /home/llv/g/b/pyball && make test
```

- [ ] **Step 2: Run lint**

```bash
cd /home/llv/g/b/pyball && make lint
```

- [ ] **Step 3: Commit any remaining changes**

```bash
cd /home/llv/g/b/pyball && git add -A && git commit -m "fix: address test/lint issues"
```

---

## Verification

After all tasks are complete, verify:

1. Legacy stats file can be loaded: `data/legacy_stats.json` (if migration has run)
2. Team balancing uses legacy assists when creating teams
3. Statistics show legacy assists in player stats
4. All existing tests pass
5. Lint passes with score 10.00/10
