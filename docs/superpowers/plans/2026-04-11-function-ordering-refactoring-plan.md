# Function Ordering Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Order functions within each Python file in the `pyball/` directory, ensuring caller functions appear before called functions.

**Architecture:** Systematic file-by-file refactoring, ensuring function definitions are ordered such that dependencies are defined after their callers (e.g., `setup_handlers` -> `handler` -> `helper`).

**Tech Stack:** Python, pytest, nox (for linting/formatting).

---

### Task 1: Refactor Infrastructure Layer
- [ ] Refactor `pyball/infrastructure/json_repository.py`: Move `_dict_to_meetup` to appear before the methods that use it.
- [ ] Refactor `pyball/infrastructure/telegram_store.py`: Ensure `_read` and `_write` are positioned correctly relative to their callers.
- [ ] Refactor `pyball/infrastructure/telegram_mapping.py` (if applicable).

### Task 2: Refactor Application Layer
- [ ] Refactor `pyball/application/meetup/*.py` files.
- [ ] Refactor `pyball/application/player/*.py` files.
- [ ] Refactor `pyball/application/container.py` and `pyball/application/fuzzy_match.py`.

### Task 3: Refactor Domain Layer
- [ ] Refactor `pyball/domain/meetup/*.py` files.
- [ ] Refactor `pyball/domain/player/*.py` files.
- [ ] Refactor `pyball/domain/base.py`.

### Task 4: Refactor Bot Layer (remaining files)
- [ ] Refactor `pyball/bot/handlers/player.py` and `pyball/bot/handlers/general.py`.
- [ ] Refactor `pyball/bot/callbacks.py`, `pyball/bot/entrypoint.py`, `pyball/bot/auth.py`, `pyball/bot/formatters.py`.
- [ ] Refactor `pyball/__main__.py` and `pyball/settings.py`.

---

**Execution Plan:**
1. For each file, analyze call graph.
2. Reorder functions in the file.
3. Run `poetry run pytest` and `poetry run nox -e lint`.
4. Commit changes.
5. Move to next file/batch.
