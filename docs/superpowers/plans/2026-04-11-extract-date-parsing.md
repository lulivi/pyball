# Extract Date Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract date parsing in `callback_handler` to a helper function.

**Architecture:** Create a private helper function `_parse_meetup_date` and call it from `callback_handler`.

**Tech Stack:** Python, `datetime`.

---

### Task 1: Create `_parse_meetup_date` helper

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Add `_parse_meetup_date` function**

```python
def _parse_meetup_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None
```

- [ ] **Step 2: Update `callback_handler` to use the helper**

```python
# Replace lines 49-53 in callback_handler
    meetup_date = _parse_meetup_date(date_str)
    if meetup_date is None:
        await query.answer("Invalid date format.", show_alert=True)
        return
```

- [ ] **Step 3: Run existing tests to ensure no regressions**

Run: `poetry run nox -e test`

- [ ] **Step 4: Commit**

```bash
git add pyball/bot/callbacks.py
git commit -m "refactor: extract _parse_meetup_date helper"
```
