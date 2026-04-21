# GoalEvent Timestamp Type Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Change `GoalEvent.timestamp` from `datetime` to `time` type, simplifying the frontend payload and storage.

**Architecture:** Change the type annotation in the domain model, update all consumers (persistence, API, use case, formatters), and fix tests. The minute calculation in formatters already works with `time` since it only uses `.hour` and `.minute` attributes.

**Tech Stack:** Python (datetime, time types), Pydantic, FastAPI, pytest

---

## File Map

| File | Change |
|------|--------|
| `pyball/domain/meetup/models.py` | Change `timestamp: datetime` to `timestamp: time` |
| `static/index.html` | Send `HH:MM` string instead of ISO datetime |
| `pyball/infrastructure/http/app.py` | `GoalEventInput.timestamp` stays `str` |
| `pyball/application/meetup/finish_match.py` | Parse with `time.fromisoformat()` |
| `pyball/infrastructure/persistence/meetup_repository.py` | Read: `.time()`, Write: unchanged |
| `pyball/bot/formatters.py` | No change needed (uses `.hour`, `.minute`) |
| `tests/unit/domain/test_meetup.py` | Use `time()` instead of `datetime()` |
| `tests/unit/bot/test_formatters.py` | Use `time()` in GoalEvent fixtures |
| `tests/unit/application/test_balance.py` | Use `time()` in GoalEvent fixtures |
| `tests/unit/application/test_compute_stats.py` | Use `time()` in GoalEvent fixtures |
| `tests/integration/test_persistence_meetup_repository.py` | Use `time()` |

---

## Task 1: Update GoalEvent Domain Model

**Files:**
- Modify: `pyball/domain/meetup/models.py:14-21`
- Test: `tests/unit/domain/test_meetup.py:41-70`

- [ ] **Step 1: Update import**

Change line 6 from `from datetime import datetime` to `from datetime import datetime, time`

- [ ] **Step 2: Update GoalEvent type annotation**

```python
@dataclass(frozen=True)
class GoalEvent(ValueObject):
    scorer_id: PlayerId
    assistant_id: PlayerId | None
    team: str
    timestamp: time  # changed from datetime
```

- [ ] **Step 3: Update tests**

In `tests/unit/domain/test_meetup.py`, change all `GoalEvent` fixtures to use `time()`:

```python
from datetime import datetime, time
# ...
ts = datetime(2026, 4, 15, 20, 30)  # change to time(20, 30)
event = GoalEvent(scorer_id=scorer, assistant_id=assistant, team="A", timestamp=time(20, 30))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/domain/test_meetup.py::TestGoalEvent -v`
Expected: PASS

- [ ] **Step 5: Run lint and format**

Run: `make format && make lint`

- [ ] **Step 6: Commit**

```bash
git add pyball/domain/meetup/models.py tests/unit/domain/test_meetup.py
git commit -m "refactor: change GoalEvent.timestamp to time type"
```

---

## Task 2: Update Persistence Repository

**Files:**
- Modify: `pyball/infrastructure/persistence/meetup_repository.py:35-45, 73-79`

- [ ] **Step 1: Update read - add `.time()` conversion**

In `_dict_to_meetup()`, change:
```python
# Antes:
timestamp=datetime.fromisoformat(e["timestamp"]),
# Después:
timestamp=datetime.fromisoformat(e["timestamp"]).time(),
```

- [ ] **Step 2: Write remains the same**

The `"timestamp": e.timestamp.isoformat()` line works unchanged with `time` type.

- [ ] **Step 3: Update tests**

In `tests/integration/test_persistence_meetup_repository.py`:
```python
# Antes:
assert loaded.result.events[0].timestamp == datetime(2026, 4, 12, 20, 15)
# Después:
from datetime import time
assert loaded.result.events[0].timestamp == time(20, 15)
```

Also update the `GoalEvent` fixture on line 107:
```python
# Antes:
event = GoalEvent(scorer_id=PlayerId(uuid4()), ... timestamp=datetime(2026, 4, 12, 20, 15))
# Después:
event = GoalEvent(scorer_id=PlayerId(uuid4()), ... timestamp=time(20, 15))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/integration/test_persistence_meetup_repository.py -v`
Expected: PASS

- [ ] **Step 5: Run lint and format**

Run: `make format && make lint`

- [ ] **Step 6: Commit**

```bash
git add pyball/infrastructure/persistence/meetup_repository.py tests/integration/test_persistence_meetup_repository.py
git commit -m "refactor: update meetup repo for time type timestamps"
```

---

## Task 3: Update FinishMatch Use Case

**Files:**
- Modify: `pyball/application/meetup/finish_match.py:1, 72-78`

- [ ] **Step 1: Update import**

```python
# Antes:
from datetime import datetime
# Después:
from datetime import datetime, time as dt_time
```

- [ ] **Step 2: Update GoalEvent creation**

```python
# Antes:
goal_events.append(
    GoalEvent(
        scorer_id=scorer_match.player_id,
        assistant_id=assistant_id,
        team=e["team"],
        timestamp=datetime.fromisoformat(e["timestamp"]),
    )
)
# Después:
goal_events.append(
    GoalEvent(
        scorer_id=scorer_match.player_id,
        assistant_id=assistant_id,
        team=e["team"],
        timestamp=dt_time.fromisoformat(e["timestamp"]),
    )
)
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/unit/application/test_meetup_use_cases.py -v`
Expected: PASS

- [ ] **Step 4: Run lint and format**

Run: `make format && make lint`

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/finish_match.py
git commit -m "refactor: parse timestamps as time in finish_match"
```

---

## Task 4: Update HTTP API Input Model

**Files:**
- Modify: `pyball/infrastructure/http/app.py`

- [ ] **Step 1: Verify GoalEventInput unchanged**

The `GoalEventInput` model already uses `timestamp: str`. No code changes needed - the Pydantic model accepts any string format.

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/ -k "finish" -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add pyball/infrastructure/http/app.py
git commit -m "chore: verify GoalEventInput accepts HH:MM timestamps"
```

---

## Task 5: Update Frontend HTML

**Files:**
- Modify: `static/index.html:139-146`

- [ ] **Step 1: Update timestamp generation**

```javascript
// Antes:
function registerGoal(assistantName = null) {
    const goalEvent = {
        type: 'gol',
        scorer: appState.tempScorer,
        assistant: assistantName,
        team: appState.tempScorerTeam,
        timestamp: new Date().toISOString()
    };

// Después:
function registerGoal(assistantName = null) {
    const goalEvent = {
        type: 'gol',
        scorer: appState.tempScorer,
        assistant: assistantName,
        team: appState.tempScorerTeam,
        timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    };
```

- [ ] **Step 2: Commit**

```bash
git add static/index.html
git commit -m "feat: send HH:MM timestamp instead of full ISO datetime"
```

---

## Task 6: Update Test Fixtures (formatters, balance, compute_stats)

**Files:**
- Modify: `tests/unit/bot/test_formatters.py`, `tests/unit/application/test_balance.py`, `tests/unit/application/test_compute_stats.py`

- [ ] **Step 1: Update formatters tests**

In `tests/unit/bot/test_formatters.py`, update `GoalEvent` fixtures:
```python
# Antes:
from datetime import datetime
# ...
event1 = GoalEvent(scorer_id=scorer_a1, assistant_id=scorer_a2, team="A", timestamp=datetime(2026, 4, 21, 20, 30))
# Después:
from datetime import time
# ...
event1 = GoalEvent(scorer_id=scorer_a1, assistant_id=scorer_a2, team="A", timestamp=time(20, 30))
```

- [ ] **Step 2: Update balance tests**

In `tests/unit/application/test_balance.py`, update all `GoalEvent` fixtures:
```python
# Antes: datetime(2026, 4, 12, 19, 30)
# Después: time(19, 30)
```

- [ ] **Step 3: Update compute_stats tests**

In `tests/unit/application/test_compute_stats.py`, update all `GoalEvent` fixtures:
```python
# Antes: datetime(2026, 4, 12, 19, 30)
# Después: time(19, 30)
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Run lint and format**

Run: `make format && make lint`

- [ ] **Step 6: Commit**

```bash
git add tests/unit/bot/test_formatters.py tests/unit/application/test_balance.py tests/unit/application/test_compute_stats.py
git commit -m "test: update GoalEvent fixtures to use time type"
```

---

## Task 7: Verify Formatters Still Work

**Files:**
- Test: `pyball/bot/formatters.py`

- [ ] **Step 1: Verify minute calculation works**

The formatter code at line 116-118 uses:
```python
minutes = (event.timestamp.hour * 60 + event.timestamp.minute) - (
    meetup.date.hour * 60 + meetup.date.minute
)
```

Both `time` and `datetime` have `.hour` and `.minute` attributes, so this works unchanged.

- [ ] **Step 2: Run formatter tests**

Run: `uv run pytest tests/unit/bot/test_formatters.py -v`
Expected: PASS

- [ ] **Step 3: Commit (if not already done in Task 6)**

```bash
git commit -m "test: verify formatters work with time type timestamps"
```

---

## Task 8: Full Integration Test

- [ ] **Step 1: Run full test suite**

Run: `make test`
Expected: ALL TESTS PASS

- [ ] **Step 2: Run lint**

Run: `make lint`
Expected: ALL CHECKS PASS

---

## Self-Review Checklist

- [ ] `GoalEvent.timestamp` is `time` type in domain model
- [ ] Frontend sends `"HH:MM"` format
- [ ] `finish_match.py` parses with `time.fromisoformat()`
- [ ] Persistence reads with `.time()`, writes with `.isoformat()`
- [ ] Formatters calculate minutes using `.hour` and `.minute`
- [ ] All test fixtures use `time()` instead of `datetime()`
- [ ] All tests pass
- [ ] Lint passes