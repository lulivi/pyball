# Infrastructure Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor infrastructure layer into logical subfolders: persistence/ for JSON repositories, telegram/ for Telegram-specific infrastructure.

**Architecture:** Split `json_repository.py` into separate files, move Telegram files into subfolder, update all imports.

**Tech Stack:** Python, no new dependencies.

---

### Task 1: Create persistence subfolder structure

**Files:**
- Create: `pyball/infrastructure/persistence/__init__.py`
- Create: `pyball/infrastructure/persistence/player_repository.py`
- Create: `pyball/infrastructure/persistence/meetup_repository.py`

- [ ] **Step 1: Create persistence folder with __init__.py**

```python
"""Persistence layer - JSON repository implementations."""

from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository

__all__ = [
    "JsonPlayerRepository",
    "JsonMeetupRepository",
]
```

- [ ] **Step 2: Create player_repository.py**

Copy the `JsonPlayerRepository` class from `pyball/infrastructure/json_repository.py` (lines 15-86).

- [ ] **Step 3: Create meetup_repository.py**

Copy the `JsonMeetupRepository` class from `pyball/infrastructure/json_repository.py` (lines 88-174).

- [ ] **Step 4: Commit**

```bash
git add pyball/infrastructure/persistence/
git commit -m "refactor(infrastructure): create persistence subfolder with player and meetup repositories"
```

---

### Task 2: Create telegram subfolder structure

**Files:**
- Create: `pyball/infrastructure/telegram/__init__.py`
- Create: `pyball/infrastructure/telegram/message_store.py`
- Create: `pyball/infrastructure/telegram/mapping.py`

- [ ] **Step 1: Create telegram folder with __init__.py**

```python
"""Telegram-specific infrastructure."""

from pyball.infrastructure.telegram.mapping import TelegramMappingStore
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore

__all__ = [
    "TelegramMessageStore",
    "MessageTracking",
    "TelegramMappingStore",
]
```

- [ ] **Step 2: Create message_store.py**

Copy content from `pyball/infrastructure/telegram_store.py` to `pyball/infrastructure/telegram/message_store.py`. Rename `TelegramMessageStore` class stays the same.

- [ ] **Step 3: Create mapping.py**

Copy content from `pyball/infrastructure/telegram_mapping.py` to `pyball/infrastructure/telegram/mapping.py`.

- [ ] **Step 4: Commit**

```bash
git add pyball/infrastructure/telegram/
git commit -m "refactor(infrastructure): create telegram subfolder with message_store and mapping"
```

---

### Task 3: Update imports in infrastructure/__init__.py

**Files:**
- Modify: `pyball/infrastructure/__init__.py`

- [ ] **Step 1: Update imports to point to new locations**

```python
"""Infrastructure layer - persistence implementations."""

from pyball.infrastructure.persistence import JsonMeetupRepository, JsonPlayerRepository
from pyball.infrastructure.telegram import TelegramMappingStore
from pyball.infrastructure.telegram import MessageTracking, TelegramMessageStore

__all__ = [
    "JsonPlayerRepository",
    "JsonMeetupRepository",
    "TelegramMessageStore",
    "MessageTracking",
    "TelegramMappingStore",
]
```

- [ ] **Step 2: Commit**

```bash
git add pyball/infrastructure/__init__.py
git commit -m "refactor(infrastructure): update imports to use new subfolder structure"
```

---

### Task 4: Update imports in application/container.py

**Files:**
- Modify: `pyball/application/container.py:15`

- [ ] **Step 1: Update infrastructure import**

Change line 15 from:
```python
from pyball.infrastructure import JsonMeetupRepository, JsonPlayerRepository
```
to:
```python
from pyball.infrastructure.persistence import JsonMeetupRepository, JsonPlayerRepository
```

- [ ] **Step 2: Run tests to verify**

Run: `poetry run nox -e test`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add pyball/application/container.py
git commit -m "refactor(container): update import to use persistence subfolder"
```

---

### Task 5: Find and update any other imports

**Files:**
- Search: All Python files importing from infrastructure

- [ ] **Step 1: Find all imports from infrastructure**

Run: `rg "from pyball.infrastructure" --type py`

- [ ] **Step 2: Update any remaining imports**

Update imports to point to new locations (persistence, telegram subfolders).

- [ ] **Step 3: Run tests to verify**

Run: `poetry run nox -e test`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "refactor: update remaining imports to use new infrastructure structure"
```

---

### Task 6: Clean up old files

**Files:**
- Delete: `pyball/infrastructure/json_repository.py`
- Delete: `pyball/infrastructure/telegram_store.py`
- Delete: `pyball/infrastructure/telegram_mapping.py`

- [ ] **Step 1: Remove old files**

```bash
rm pyball/infrastructure/json_repository.py
rm pyball/infrastructure/telegram_store.py
rm pyball/infrastructure/telegram_mapping.py
```

- [ ] **Step 2: Run tests to verify**

Run: `poetry run nox -e test`
Expected: All tests pass

- [ ] **Step 3: Run lint to verify**

Run: `poetry run nox -e lint`
Expected: No issues

- [ ] **Step 4: Commit**

```bash
git rm pyball/infrastructure/json_repository.py pyball/infrastructure/telegram_store.py pyball/infrastructure/telegram_mapping.py
git commit -m "refactor(infrastructure): remove old files after reorganization"
```