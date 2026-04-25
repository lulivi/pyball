# Design: Legacy Assists Support

## Problem

The migration script `scripts/migrate_legacy_sqlite_to_json.py` migrates historical data from SQLite to JSON, but assists are stored as `assistant_id: None` because the legacy schema only stores aggregate counts per player, not which scorer each assist belonged to.

This affects:
1. **Team balancing**: Players with many historical assists don't get credited when creating balanced teams.
2. **Statistics**: Historical stats show 0 assists for players who had many in the legacy era.

## Solution

Keep legacy aggregate data separate from the DDD model, as an external reference.

### 1. Legacy Stats File

**Location**: `data/legacy_stats.json`

**Structure**:
```json
{
  "players": {
    "<player_uuid>": {
      "goals": 25,
      "assists": 12,
      "matches": 30
    }
  }
}
```

**Generation**: The migration script already reads `goals` and `assists` from `match_statistic`. It just needs to write this additional file.

### 2. Legacy Stats Loader

**New class**: `pyball.infrastructure.persistence.legacy_stats.LegacyStats`

```python
class LegacyStats:
    def __init__(self, data: dict[str, dict[str, int]]): ...
    def get(self, player_id: str) -> dict[str, int]: ...  # {goals, assists, matches}
    def get_assists(self, player_id: str) -> int: ...
    def get_goals(self, player_id: str) -> int: ...
    def get_matches(self, player_id: str) -> int: ...
    def all_players(self) -> list[str]: ...
```

**Loading**: Loaded once at app startup via `Container`.

### 3. Integration in balance.py

In `_player_stats()`:

```python
def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,  # new parameter
) -> tuple[int, float, float, float]:
    # ... existing logic ...
    for event in meetup.result.events:
        if event.scorer_id == player_id:
            goals += 1
        if event.assistant_id == player_id:
            assists += 1

    # Add legacy assists
    if legacy_stats and mp > 0:
        legacy = legacy_stats.get(player_id)
        assists += legacy["assists"]
```

Update `_player_role()` similarly.

### 4. Integration in compute_stats.py

In `_compute_player_stats()` (~line 150), add `legacy_stats: LegacyStats | None` parameter and sum legacy assists.

### 5. Container Update

In `pyball/application/container.py`:

1. Add `legacy_stats: LegacyStats` as a dependency.
2. Load from `data/legacy_stats.json` if it exists (if not, `LegacyStats({})`).

### 6. Migration Script

Modify `scripts/migrate_legacy_sqlite_to_json.py`:

- It already reads `goals` and `assists` from `match_statistic` (line 88).
- Add a function to aggregate by player and write `legacy_stats.json` to `data/`.

## Test Data

Existing test `tests/unit/application/test_balance.py` uses `GoalEvent` without `assistant_id`. Tests must continue to pass — the logic only adds assists when `legacy_stats` has data.

## Notes

- Legacy data is **read-only** — never modified.
- If a player has stats in both meetups and legacy, they are summed.
- If `legacy_stats.json` doesn't exist, the system works the same (backwards compatibility).
