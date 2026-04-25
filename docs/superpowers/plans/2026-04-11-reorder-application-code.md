# Reorder Application Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder classes/functions in `pyball/application/meetup/` files according to the caller-before-callee rule.

**Architecture:** Move classes/functions so that those which call others appear before those they call.

**Tech Stack:** Python, pytest, nox.

---

### Task 1: Reorder `create_meetup.py`

**Files:**
- Modify: `/home/llv/g/b/pyball/pyball/application/meetup/create_meetup.py`

- [ ] **Step 1: Move `CreateMeetup` class before `DuplicateMeetupError`**
- [ ] **Step 2: Run tests**
    Run: `poetry run pytest`
- [ ] **Step 3: Run lint**
    Run: `poetry run nox -e lint`
- [ ] **Step 4: Commit**
    Run: `git add pyball/application/meetup/create_meetup.py && git commit -m "refactor: reorder classes in create_meetup.py"`

### Task 2: Reorder `create_teams.py`

**Files:**
- Modify: `/home/llv/g/b/pyball/pyball/application/meetup/create_teams.py`

- [ ] **Step 1: Move `CreateTeams` class before `InvalidMeetupDateError`**
- [ ] **Step 2: Run tests**
    Run: `poetry run pytest`
- [ ] **Step 3: Run lint**
    Run: `poetry run nox -e lint`
- [ ] **Step 4: Commit**
    Run: `git add pyball/application/meetup/create_teams.py && git commit -m "refactor: reorder classes in create_teams.py"`

### Task 3: Verify `add_player.py` and `remove_player.py`

These files only contain one class (`AddPlayerToMeetup` and `RemovePlayerFromMeetup` respectively), so no reordering is needed, but I should verify they are still correct.

- [ ] **Step 1: Run tests**
    Run: `poetry run pytest`
- [ ] **Step 2: Run lint**
    Run: `poetry run nox -e lint`
- [ ] **Step 3: Commit**
    Run: `git add pyball/application/meetup/add_player.py pyball/application/meetup/remove_player.py && git commit -m "refactor: verify order in add_player.py and remove_player.py"`
