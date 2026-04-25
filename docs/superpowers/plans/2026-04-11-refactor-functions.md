# Refactoring Plan

## Goal
Reorder functions and properties in `pyball/application/container.py` and `pyball/application/fuzzy_match.py` to follow the "caller-before-callee" (top-down) order.

## Plan

### Task 1: Refactor `pyball/application/container.py`
- Modify: `pyball/application/container.py`
- Reorder `Container` class members so that high-level methods (e.g., `create_player`, `rename_player`) appear before property definitions (`player_repository`, `meetup_repository`).
- Test: `poetry run pytest`

### Task 2: Refactor `pyball/application/fuzzy_match.py`
- Modify: `pyball/application/fuzzy_match.py`
- Move `fuzzy_match_player` above `FuzzyMatchResult`.
- Test: `poetry run pytest`

### Task 3: Verify and Commit
- Run: `poetry run nox -e lint`
- Git: Commit changes if everything passes.
