# Legacy Stats with Timestamps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add datetime information to legacy statistics so that filtering by date range (e.g., season start) is possible for team generation and stats display.

**Architecture:** Legacy stats will store granular match-by-match data with timestamps instead of aggregate totals. New filtering methods will allow date-based filtering. CreateTeams, Balance, and ComputeStats will pass `from_date` to filter legacy stats.

**Tech Stack:** Python, pytest, no external deps

---

### Task 1: Update LegacyStats class for granular data

**Files:**
- Modify: `pyball/infrastructure/persistence/legacy_stats.py:1-45`
- Test: `tests/unit/infrastructure/test_legacy_stats.py`

- [ ] **Step 1: Write failing tests for new filtering methods**

```python
@dataclass
class LegacyStats:
    def get_goals_since(self, player_id: str, since: datetime) -> int:
        """Return total goals since the given datetime."""
        ...

    def get_assists_since(self, player_id: str, since: datetime) -> int:
        """Return total assists since the given datetime."""
        ...

    def get_matches_since(self, player_id: str, since: datetime) -> int:
        """Return total matches since the given datetime."""
        ...
```

Add to test file:

```python
def test_get_goals_since_filters_by_date():
    data = {
        "players": {
            "uuid-1": {
                "goals": 10,
                "assists": 5,
                "matches": 3,
                "goals_by_match": [
                    {"date": "2023-01-01T10:00:00", "count": 3},
                    {"date": "2023-02-01T10:00:00", "count": 5},
                    {"date": "2023-03-01T10:00:00", "count": 2},
                ],
                "assists_by_match": [
                    {"date": "2023-01-01T10:00:00", "count": 2},
                    {"date": "2023-02-01T10:00:00", "count": 3},
                ]
            }
        }
    }
    stats = LegacyStats(data)
    from datetime import datetime
    # Filter from Feb 2023 - should only count Feb + Mar
    assert stats.get_goals_since("uuid-1", datetime(2023, 2, 1)) == 7
    assert stats.get_assists_since("uuid-1", datetime(2023, 2, 1)) == 3
    # Filter from Mar 2023 - should only count Mar
    assert stats.get_goals_since("uuid-1", datetime(2023, 3, 1)) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/infrastructure/test_legacy_stats.py -v`
Expected: FAIL with AttributeError or similar

- [ ] **Step 3: Implement new methods in legacy_stats.py**

```python
from datetime import datetime

@dataclass
class LegacyStats:
    _data: dict[str, dict[str, dict[str, int] | list[dict[str, Any]]]]

    def get_goals_since(self, player_id: str, since: datetime) -> int:
        """Return total goals since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "goals_by_match" not in player_data:
            return player_data.get("goals", 0)
        total = 0
        since_iso = since.isoformat()
        for entry in player_data["goals_by_match"]:
            if entry["date"] >= since_iso:
                total += entry["count"]
        return total

    def get_assists_since(self, player_id: str, since: datetime) -> int:
        """Return total assists since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "assists_by_match" not in player_data:
            return player_data.get("assists", 0)
        total = 0
        since_iso = since.isoformat()
        for entry in player_data["assists_by_match"]:
            if entry["date"] >= since_iso:
                total += entry["count"]
        return total

    def get_matches_since(self, player_id: str, since: datetime) -> int:
        """Return total matches since the given datetime."""
        player_data = self._data.get("players", {}).get(player_id, {})
        if "goals_by_match" not in player_data and "assists_by_match" not in player_data:
            return player_data.get("matches", 0)
        match_dates: set[str] = set()
        for entry in player_data.get("goals_by_match", []):
            if entry["date"] >= since.isoformat():
                match_dates.add(entry["date"])
        for entry in player_data.get("assists_by_match", []):
            if entry["date"] >= since.isoformat():
                match_dates.add(entry["date"])
        return len(match_dates)
```

Also update the existing `get()` method to work with new structure:

```python
def get(self, player_id: str) -> dict[str, int]:
    """Return {goals, assists, matches} for player_id, or zeros if not found."""
    player_data = self._data.get("players", {}).get(player_id, {})
    if not player_data:
        return {"goals": 0, "assists": 0, "matches": 0}
    # If using new granular format, compute totals
    if "goals_by_match" in player_data:
        goals = sum(e["count"] for e in player_data["goals_by_match"])
        assists = sum(e["count"] for e in player_data.get("assists_by_match", []))
        matches = len(set(e["date"] for e in player_data.get("goals_by_match", []) 
                       + player_data.get("assists_by_match", [])))
        return {"goals": goals, "assists": assists, "matches": matches}
    # Legacy aggregate format
    return {
        "goals": player_data.get("goals", 0),
        "assists": player_data.get("assists", 0),
        "matches": player_data.get("matches", 0),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/infrastructure/test_legacy_stats.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/infrastructure/persistence/legacy_stats.py tests/unit/infrastructure/test_legacy_stats.py
git commit -m "feat(legacy_stats): add granular timestamp-based filtering methods"
```

---

### Task 2: Update migrate script to generate granular data

**Files:**
- Modify: `scripts/migrate_legacy_sqlite_to_json.py:180-209`
- Test: Create manual test by running migration script (no unit test needed)

- [ ] **Step 1: Update _generate_legacy_stats function**

Replace the existing `_generate_legacy_stats` function (lines 180-209) with:

```python
def _generate_legacy_stats(
    conn: sqlite3.Connection,
    old_id_to_uuid: dict[int, str],
    output_dir: Path,
) -> None:
    """Generate legacy_stats.json with granular goals/assists per match."""
    cur = conn.execute(
        "SELECT date, player_id, team, goals, assists FROM match_statistic ORDER BY date"
    )
    rows = cur.fetchall()

    players_data: dict[str, dict[str, Any]] = {}

    for row in rows:
        player_uuid = old_id_to_uuid.get(row["player_id"])
        if player_uuid is None:
            continue
        date_iso = row["date"]  # format: "2023-01-15"

        if player_uuid not in players_data:
            players_data[player_uuid] = {
                "goals_by_match": [],
                "assists_by_match": [],
            }

        players_data[player_uuid]["goals_by_match"].append({
            "date": date_iso + "T10:00:00",
            "count": row["goals"],
        })
        players_data[player_uuid]["assists_by_match"].append({
            "date": date_iso + "T10:00:00",
            "count": row["assists"],
        })

    # Compute totals for backward compatibility
    legacy: dict[str, dict[str, Any]] = {"players": {}}
    for player_uuid, data in players_data.items():
        goals = sum(e["count"] for e in data["goals_by_match"])
        assists = sum(e["count"] for e in data["assists_by_match"])
        matches = len(set(e["date"] for e in data["goals_by_match"]))

        legacy["players"][player_uuid] = {
            "goals": goals,
            "assists": assists,
            "matches": matches,
            "goals_by_match": data["goals_by_match"],
            "assists_by_match": data["assists_by_match"],
        }

    legacy_file = output_dir / "legacy_stats.json"
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(legacy, f, indent=2, ensure_ascii=False)

    print(f"  Legacy stats: {len(legacy['players'])} players written to {legacy_file}")
```

---

### Task 3: Update CreateTeams to pass from_date to legacy stats

**Files:**
- Modify: `pyball/application/meetup/create_teams.py:37-66`
- Test: Integration test via bot commands (manual verification)

- [ ] **Step 1: Update CreateTeams to filter legacy stats by season**

The code already computes `season_start` - we need to pass it to the legacy stats:

```python
def execute(self, date_str: str) -> Meetup:
    """Create balanced teams for a meetup by date string."""
    try:
        meetup_date = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
    except ValueError as exc:
        raise InvalidMeetupDateError("Invalid date format. Use: YYYY/MM/DD HH:MM") from exc

    meetup = self.meetup_repository.find_by_date(meetup_date.date())
    if not meetup:
        raise MeetupNotFoundError(date_str)

    all_meetups = self.meetup_repository.find_all()
    finished = [m for m in all_meetups if m.result is not None]
    season_start = _season_start(date.today())
    season_meetups = [m for m in finished if m.date.date() >= season_start]

    # Convert season_start to datetime for legacy stats filtering
    from datetime import datetime as dt
    season_start_dt = dt.combine(season_start, dt.min.time())

    player_scores = compute_player_scores(
        meetup.players, season_meetups, finished, self.legacy_stats, season_start_dt
    )
    player_roles = compute_player_roles(
        meetup.players, season_meetups, finished, self.legacy_stats, season_start_dt
    )
    winning_counts = extract_winning_counts(finished)
    team_a_ids, team_b_ids = optimize_teams(
        meetup.players, player_scores, winning_counts, player_roles
    )

    meetup.set_teams([Team.create("A", team_a_ids), Team.create("B", team_b_ids)])
    self.meetup_repository.save(meetup)
    return meetup
```

- [ ] **Step 2: Commit**

```bash
git add pyball/application/meetup/create_teams.py
git commit -m "feat(create_teams): filter legacy stats by season start date"
```

---

### Task 4: Update balance.py to accept optional from_date parameter

**Files:**
- Modify: `pyball/application/meetup/balance.py:21-52`, `:106-141`, `:144-157`
- Test: Integration via create_teams

- [ ] **Step 1: Update _player_stats to accept optional from_date**

```python
from datetime import datetime

def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> tuple[int, float, float, float]:
    """Return (matches_played, goals_per_match, assists_per_match, win_rate)."""
    goals = assists = wins = mp = 0
    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue
        score_a = meetup.result.score_a
        score_b = meetup.result.score_b
        for team in meetup.teams:
            if player_id in team.players:
                mp += 1
                team_wins = (team.name == "A" and score_a > score_b) or (
                    team.name == "B" and score_b > score_a
                )
                if team_wins:
                    wins += 1
        for event in meetup.result.events:
            if event.scorer_id == player_id:
                goals += 1
            if event.assistant_id == player_id:
                assists += 1
    if legacy_stats and mp > 0:
        pid_str = str(player_id.value)
        if from_date is not None:
            assists += legacy_stats.get_assists_since(pid_str, from_date)
        else:
            legacy = legacy_stats.get(pid_str)
            assists += legacy["assists"]

    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp
```

- [ ] **Step 2: Update compute_player_scores signature**

```python
def compute_player_scores(
    player_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> dict[PlayerId, float]:
```

And update the calls inside to pass `from_date`:

```python
    for pid in player_ids:
        mp_s, gpm_s, apm_s, wr_s = _player_stats(pid, season_meetups, legacy_stats, from_date)
        if mp_s >= _SEASON_MIN_MATCHES:
            components[pid] = (gpm_s, apm_s, wr_s)
        else:
            mp_a, gpm_a, apm_a, wr_a = _player_stats(pid, all_meetups, legacy_stats, from_date)
            components[pid] = (gpm_a, apm_a, wr_a) if mp_a > 0 else None
```

- [ ] **Step 3: Update compute_player_roles signature**

```python
def compute_player_roles(
    player_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
    legacy_stats: LegacyStats | None = None,
    from_date: datetime | None = None,
) -> dict[PlayerId, str]:
```

And update the call inside:

```python
    return {
        pid: _player_role(pid, season_meetups, all_meetups, legacy_stats) for pid in player_ids
    }
```

- [ ] **Step 4: Commit**

```bash
git add pyball/application/meetup/balance.py
git commit -m "feat(balance): support date filtering for legacy stats"
```

---

### Task 5: Update compute_stats.py to accept from_date

**Files:**
- Modify: `pyball/application/meetup/compute_stats.py`
- Test: Integration via bot commands

- [ ] **Step 1: Find and update functions that use legacy_stats**

Search for functions in compute_stats.py that accept and use legacy_stats parameter, then update them to accept `from_date` and pass it through to `compute_player_scores` and `compute_player_roles`.

- [ ] **Step 2: Commit**

```bash
git add pyball/application/meetup/compute_stats.py
git commit -m "feat(compute_stats): support date filtering for legacy stats"
```

---

### Task 6: Run full test suite

**Files:**
- Run: `make test`

- [ ] **Step 1: Run full test suite**

Run: `make test`
Expected: All tests pass

- [ ] **Step 2: Run lint**

Run: `make lint`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git commit -m "test: run full test suite"
```

---

**Plan saved to:** `docs/superpowers/plans/2026-04-20-legacy-stats-with-timestamps-plan.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**