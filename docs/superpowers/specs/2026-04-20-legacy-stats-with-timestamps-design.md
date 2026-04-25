# Legacy Stats with Timestamps Design

## Overview

Add datetime information to legacy statistics so that filtering by date range (e.g., season start) is possible for team generation and stats display.

## Data Structure

```json
{
  "players": {
    "<uuid>": {
      "goals": 10,
      "assists": 5,
      "matches": 8,
      "goals_by_match": [
        {"date": "2023-01-15T10:00:00", "count": 2},
        {"date": "2023-01-22T10:00:00", "count": 1}
      ],
      "assists_by_match": [
        {"date": "2023-01-15T10:00:00", "count": 1},
        {"date": "2023-01-22T10:00:00", "count": 2}
      ]
    }
  }
}
```

## Changes Required

### 1. migrate_legacy_sqlite_to_json.py

- Modify `_generate_legacy_stats()` to group by match date
- Store arrays with `{date, count}` instead of simple totals
- Extract date from `match_statistic.date` field

### 2. legacy_stats.py

- Add `get_assists_since(date)` - filter assists from date onwards
- Add `get_goals_since(date)` - filter goals from date onwards
- Add `get_matches_since(date)` - filter match count from date onwards
- Keep `get()` for backward compatibility (returns totals)

### 3. CreateTeams use case

- Accept optional `from_date` parameter
- Pass `from_date` to legacy stats filtering when calculating player ratings

### 4. Balance use case

- Accept optional `from_date` parameter
- Filter legacy stats by date when computing balance

### 5. ComputeStats use case

- Accept optional `from_date` parameter
- Filter legacy stats by date for season reports

## Backward Compatibility

- If `from_date` is not provided, use full totals (existing behavior)
- `get()` method remains unchanged returning aggregate totals
