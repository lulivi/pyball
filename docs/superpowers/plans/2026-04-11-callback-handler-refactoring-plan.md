# Callback Handler Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `pyball/bot/callbacks.py` by extracting logic into smaller, testable functions (Functional Modularization).

**Architecture:** The `callback_handler` function will be simplified into a high-level orchestrator that delegates to helper functions.

**Tech Stack:** Python, `python-telegram-bot`

---

### Task 1: Extract Date Parsing

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Define `_parse_meetup_date` helper**
```python
def _parse_meetup_date(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None
```

- [ ] **Step 2: Update `callback_handler` to use helper**
Replace the inline date parsing with a call to `_parse_meetup_date`.

### Task 2: Extract Meetup Retrieval

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Define `_find_meetup` helper**
```python
def _find_meetup(meetup_repo, date: datetime) -> Meetup | None:
    all_meetups = meetup_repo.find_all()
    for m in all_meetups:
        if m.date.date() == date.date():
            return m
    return None
```

- [ ] **Step 2: Update `callback_handler` to use helper**
Replace the inline meetup search with a call to `_find_meetup`.

### Task 3: Extract Player Identification

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Define `_get_player` helper**
```python
def _get_player(telegram_id: int, mapping_store: TelegramMappingStore, player_repo) -> PlayerId | None:
    player_id_str = mapping_store.get_player_id(telegram_id)
    if not player_id_str:
        return None
    try:
        return PlayerId.from_string(player_id_str)
    except InvalidPlayerIdError:
        return None
```

- [ ] **Step 2: Update `callback_handler` to use helper**
Replace the inline player ID retrieval and validation with a call to `_get_player`.

### Task 4: Extract Action Processing

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Define `_process_action` helper**
```python
def _process_action(action: str, meetup: Meetup, player_id: PlayerId) -> bool:
    if action == "join":
        if player_id not in meetup.players:
            meetup.add_player(player_id)
            return True
        return False
    elif action == "leave":
        try:
            meetup.remove_player(player_id)
            return True
        except Exception:
            return False
    return False
```

- [ ] **Step 2: Update `callback_handler` to use helper**
Replace the inline action processing logic with a call to `_process_action`.

### Task 5: Verify and Clean Up

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Run tests**
Run: `poetry run nox -e test`

- [ ] **Step 2: Format and Lint**
Run: `poetry run nox -e format && poetry run nox -e lint`

- [ ] **Step 3: Commit**
```bash
git add pyball/bot/callbacks.py
git commit -m "refactor: extract helper functions in callback_handler"
```
