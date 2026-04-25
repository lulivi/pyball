# Balanced Teams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace random team creation with a history-aware optimization algorithm that produces balanced, repeatable-but-varied team assignments.

**Architecture:** A new pure-logic module `balance.py` computes normalized player strength scores from historical goals/assists/win-rate and optimizes team assignments via local search. `CreateTeams` use case is updated to call this module instead of `create_random_teams()`. A new `set_teams()` method on `Meetup` provides a clean domain API.

**Tech Stack:** Python stdlib (`random`, `itertools`), pytest, existing domain models (`Meetup`, `Team`, `PlayerId`, `MatchResult`)

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `pyball/domain/meetup/models.py` | Add `set_teams()` method to `Meetup` |
| Create | `pyball/application/meetup/balance.py` | Pure scoring + optimization logic |
| Modify | `pyball/application/meetup/create_teams.py` | Wire balance module; remove random fallback |
| Modify | `tests/unit/domain/test_meetup.py` | Tests for `set_teams()` |
| Create | `tests/unit/application/test_balance.py` | Tests for all balance functions |
| Modify | `tests/unit/application/test_meetup_use_cases.py` | Update/extend `TestCreateTeams` |

---

## Task 1: Add `set_teams()` to the Meetup domain model

**Files:**
- Modify: `pyball/domain/meetup/models.py` (after line 85, inside `Meetup` class)
- Modify: `tests/unit/domain/test_meetup.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/domain/test_meetup.py` inside `class TestMeetup`:

```python
def test_set_teams_assigns_two_teams(self):
    """set_teams stores two teams on the meetup."""
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    meetup.set_teams(teams)
    assert meetup.teams == teams

def test_set_teams_requires_exactly_two(self):
    """set_teams raises ValueError when not given exactly two teams."""
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    with pytest.raises(ValueError, match="Exactly two teams required"):
        meetup.set_teams([Team.create("A", [])])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -e test -- tests/unit/domain/test_meetup.py::TestMeetup::test_set_teams_assigns_two_teams tests/unit/domain/test_meetup.py::TestMeetup::test_set_teams_requires_exactly_two -v
```

Expected: FAIL with `AttributeError: 'Meetup' object has no attribute 'set_teams'`

- [ ] **Step 3: Implement `set_teams()` in `Meetup`**

In `pyball/domain/meetup/models.py`, add after the `is_closed` method (after line 85):

```python
def set_teams(self, teams: list[Team]) -> None:
    """Assign pre-computed teams to this meetup."""
    if len(teams) != 2:
        raise ValueError("Exactly two teams required")
    self.teams = teams
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -e test -- tests/unit/domain/test_meetup.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/domain/meetup/models.py tests/unit/domain/test_meetup.py
git commit -m "feat: add set_teams() to Meetup domain model"
```

---

## Task 2: Create `balance.py` — player scoring

**Files:**
- Create: `pyball/application/meetup/balance.py`
- Create: `tests/unit/application/test_balance.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/application/test_balance.py`:

```python
"""Tests for the balanced-teams scoring logic."""

from datetime import datetime

import pytest

from pyball.application.meetup.balance import compute_player_scores
from pyball.domain.meetup.models import MatchResult, Meetup, PlayerId, Team


def _finished_meetup(
    date_str: str,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
    events: tuple = (),
) -> Meetup:
    """Build a finished Meetup for testing."""
    m = Meetup.create(datetime.strptime(date_str, "%Y-%m-%d %H:%M"), "Campo")
    for pid in team_a + team_b:
        m.add_player(pid)
    m.set_teams([Team.create("A", team_a), Team.create("B", team_b)])
    m.set_result(MatchResult(score_a=score_a, score_b=score_b, events=events))
    return m


class TestComputePlayerScores:
    """Tests for compute_player_scores."""

    def test_winner_scores_higher_than_loser(self):
        """Player who always wins gets a higher score than player who always loses."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetups = [
            _finished_meetup(f"2025-10-0{i} 20:00", [p1], [p2], 2, 0)
            for i in range(1, 4)
        ]
        scores = compute_player_scores([p1, p2], meetups, meetups)
        assert scores[p1] > scores[p2]

    def test_falls_back_to_all_time_when_below_season_threshold(self):
        """Player with < 3 season matches uses full-history data instead."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        # 2 season matches — p1 wins both (below threshold)
        season = [
            _finished_meetup("2025-10-01 20:00", [p1], [p2], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1], [p2], 2, 0),
        ]
        # 3 old matches — p2 wins all (makes p2 stronger in full history)
        old = [
            _finished_meetup("2024-10-01 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-08 20:00", [p2], [p1], 2, 0),
            _finished_meetup("2024-10-15 20:00", [p2], [p1], 2, 0),
        ]
        all_meetups = season + old
        scores = compute_player_scores([p1, p2], season, all_meetups)
        # Both below threshold → both use full history → p2 wins 3/5 vs p1 2/5
        assert scores[p2] > scores[p1]

    def test_no_history_player_gets_group_average(self):
        """Player with no match history receives the mean of all other players' scores."""
        p1, p2, p_new = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
        meetups = [
            _finished_meetup(f"2025-10-0{i} 20:00", [p1], [p2], 2, 0)
            for i in range(1, 4)
        ]
        scores = compute_player_scores([p1, p2, p_new], meetups, meetups)
        expected_mean = (scores[p1] + scores[p2]) / 2
        assert abs(scores[p_new] - expected_mean) < 1e-9

    def test_all_scores_in_unit_interval(self):
        """Every returned score is in [0.0, 1.0]."""
        players = [PlayerId.generate() for _ in range(4)]
        p_a, p_b = players[:2], players[2:]
        meetups = [
            _finished_meetup("2025-10-01 20:00", p_a, p_b, 3, 1),
            _finished_meetup("2025-10-08 20:00", p_b, p_a, 2, 0),
            _finished_meetup("2025-10-15 20:00", p_a, p_b, 1, 0),
        ]
        scores = compute_player_scores(players, meetups, meetups)
        for pid, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score out of range for {pid}: {score}"

    def test_all_no_history_returns_half(self):
        """When no player has history, everyone gets 0.5."""
        players = [PlayerId.generate() for _ in range(3)]
        scores = compute_player_scores(players, [], [])
        for score in scores.values():
            assert score == pytest.approx(0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -e test -- tests/unit/application/test_balance.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pyball.application.meetup.balance'`

- [ ] **Step 3: Implement `balance.py` with player scoring**

Create `pyball/application/meetup/balance.py`:

```python
"""Balanced team creation: player scoring and team optimization."""

from __future__ import annotations

import itertools
import random

from pyball.domain.meetup.models import Meetup, PlayerId

_SEASON_MIN_MATCHES = 3
_W_GOALS = 0.40
_W_ASSISTS = 0.30
_W_WINS = 0.30
_PAIR_WEIGHT = 1.0
_ITERATIONS = 500


def _player_stats(
    player_id: PlayerId,
    meetups: list[Meetup],
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
    if mp == 0:
        return 0, 0.0, 0.0, 0.0
    return mp, goals / mp, assists / mp, wins / mp


def _normalize(values: list[float]) -> list[float]:
    """Normalize a list of floats to [0, 1]. Returns [0.5, ...] if all equal."""
    min_v, max_v = min(values), max(values)
    if max_v == min_v:
        return [0.5] * len(values)
    return [(v - min_v) / (max_v - min_v) for v in values]


def compute_player_scores(
    player_ids: list[PlayerId],
    season_meetups: list[Meetup],
    all_meetups: list[Meetup],
) -> dict[PlayerId, float]:
    """Return a normalized [0, 1] strength score for each player.

    Uses season data when a player has >= _SEASON_MIN_MATCHES there, otherwise
    falls back to full history. Players with no history receive the group mean.
    """
    components: dict[PlayerId, tuple[float, float, float] | None] = {}
    for pid in player_ids:
        mp_s, gpm_s, apm_s, wr_s = _player_stats(pid, season_meetups)
        if mp_s >= _SEASON_MIN_MATCHES:
            components[pid] = (gpm_s, apm_s, wr_s)
        else:
            mp_a, gpm_a, apm_a, wr_a = _player_stats(pid, all_meetups)
            components[pid] = (gpm_a, apm_a, wr_a) if mp_a > 0 else None

    known = [(pid, c) for pid, c in components.items() if c is not None]
    if not known:
        return {pid: 0.5 for pid in player_ids}

    known_pids = [pid for pid, _ in known]
    norm_goals = _normalize([c[0] for _, c in known])
    norm_assists = _normalize([c[1] for _, c in known])
    norm_wins = _normalize([c[2] for _, c in known])

    known_scores = {
        pid: norm_goals[i] * _W_GOALS + norm_assists[i] * _W_ASSISTS + norm_wins[i] * _W_WINS
        for i, pid in enumerate(known_pids)
    }

    mean_score = sum(known_scores.values()) / len(known_scores)
    return {pid: known_scores.get(pid, mean_score) for pid in player_ids}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -e test -- tests/unit/application/test_balance.py::TestComputePlayerScores -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/balance.py tests/unit/application/test_balance.py
git commit -m "feat: add compute_player_scores to balance module"
```

---

## Task 3: Add `extract_winning_counts()` to `balance.py`

**Files:**
- Modify: `pyball/application/meetup/balance.py`
- Modify: `tests/unit/application/test_balance.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/application/test_balance.py`:

```python
class TestExtractWinningCounts:
    """Tests for extract_winning_counts."""

    def test_counts_shared_wins_for_pairs(self):
        """Players who win together accumulate a shared win count."""
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        # p1+p2 win twice, p3+p4 win once
        meetups = [
            _finished_meetup("2025-10-01 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-08 20:00", [p1, p2], [p3, p4], 2, 0),
            _finished_meetup("2025-10-15 20:00", [p3, p4], [p1, p2], 2, 0),
        ]
        from pyball.application.meetup.balance import extract_winning_counts

        counts = extract_winning_counts(meetups)

        key_12 = tuple(sorted([str(p1.value), str(p2.value)]))
        key_34 = tuple(sorted([str(p3.value), str(p4.value)]))
        assert counts[key_12] == 2
        assert counts[key_34] == 1

    def test_empty_when_no_meetups(self):
        """An empty meetup list returns empty counts."""
        from pyball.application.meetup.balance import extract_winning_counts

        assert extract_winning_counts([]) == {}

    def test_keys_are_sorted_string_pairs(self):
        """All dict keys are (str, str) tuples with the smaller UUID string first."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup = _finished_meetup("2025-10-01 20:00", [p1, p2], [], 2, 0)
        from pyball.application.meetup.balance import extract_winning_counts

        counts = extract_winning_counts([meetup])

        for key in counts:
            assert isinstance(key, tuple) and len(key) == 2
            assert key[0] <= key[1]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -e test -- tests/unit/application/test_balance.py::TestExtractWinningCounts -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_winning_counts'`

- [ ] **Step 3: Add `extract_winning_counts()` to `balance.py`**

Append to `pyball/application/meetup/balance.py` (before the end of the file):

```python
def extract_winning_counts(meetups: list[Meetup]) -> dict[tuple[str, str], int]:
    """Return sorted (pid_a, pid_b) → shared win count for all player pairs."""
    counts: dict[tuple[str, str], int] = {}
    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue
        score_a = meetup.result.score_a
        score_b = meetup.result.score_b
        for team in meetup.teams:
            team_wins = (team.name == "A" and score_a > score_b) or (
                team.name == "B" and score_b > score_a
            )
            if team_wins:
                for pid_a, pid_b in itertools.combinations(team.players, 2):
                    key = tuple(sorted([str(pid_a.value), str(pid_b.value)]))
                    counts[key] = counts.get(key, 0) + 1
    return counts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -e test -- tests/unit/application/test_balance.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/balance.py tests/unit/application/test_balance.py
git commit -m "feat: add extract_winning_counts to balance module"
```

---

## Task 4: Add `optimize_teams()` to `balance.py`

**Files:**
- Modify: `pyball/application/meetup/balance.py`
- Modify: `tests/unit/application/test_balance.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/application/test_balance.py`:

```python
class TestOptimizeTeams:
    """Tests for optimize_teams."""

    def test_all_players_assigned_exactly_once(self):
        """Every input player appears in exactly one output team."""
        from pyball.application.meetup.balance import optimize_teams

        player_ids = [PlayerId.generate() for _ in range(6)]
        scores = {pid: 0.5 for pid in player_ids}

        team_a, team_b = optimize_teams(player_ids, scores, {})

        all_assigned = team_a + team_b
        assert len(all_assigned) == len(player_ids)
        assert set(all_assigned) == set(player_ids)

    def test_raises_with_fewer_than_two_players(self):
        """optimize_teams raises ValueError for fewer than 2 players."""
        from pyball.application.meetup.balance import optimize_teams

        pid = PlayerId.generate()
        with pytest.raises(ValueError, match="Need at least 2"):
            optimize_teams([pid], {pid: 0.5}, {})

    def test_teams_split_evenly(self):
        """Teams differ in size by at most 1 player."""
        from pyball.application.meetup.balance import optimize_teams

        player_ids = [PlayerId.generate() for _ in range(7)]
        scores = {pid: 0.5 for pid in player_ids}

        team_a, team_b = optimize_teams(player_ids, scores, {})

        assert abs(len(team_a) - len(team_b)) <= 1

    def test_produces_varied_results(self):
        """Repeated calls with identical input produce more than one distinct composition."""
        from pyball.application.meetup.balance import optimize_teams

        player_ids = [PlayerId.generate() for _ in range(4)]
        scores = {pid: 0.5 for pid in player_ids}

        compositions = set()
        for _ in range(30):
            team_a, _ = optimize_teams(player_ids, scores, {})
            compositions.add(frozenset(team_a))

        assert len(compositions) > 1

    def test_winning_pair_bonus_influences_balance(self):
        """A dominant winning pair is separated when it reduces the score imbalance."""
        from pyball.application.meetup.balance import extract_winning_counts, optimize_teams

        # p1 and p2 have won together 10 times; p3 and p4 have no shared history
        p1, p2, p3, p4 = [PlayerId.generate() for _ in range(4)]
        key = tuple(sorted([str(p1.value), str(p2.value)]))
        winning_counts = {key: 10}
        scores = {p1: 0.5, p2: 0.5, p3: 0.5, p4: 0.5}

        # Run many times: p1 and p2 should end up on different teams more often than not
        same_team_count = 0
        trials = 100
        for _ in range(trials):
            team_a, team_b = optimize_teams([p1, p2, p3, p4], scores, winning_counts)
            if p1 in team_a and p2 in team_a:
                same_team_count += 1
            if p1 in team_b and p2 in team_b:
                same_team_count += 1

        # Separated more than 50% of the time (pair bonus discourages co-location)
        assert same_team_count < trials * 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -e test -- tests/unit/application/test_balance.py::TestOptimizeTeams -v
```

Expected: FAIL with `ImportError: cannot import name 'optimize_teams'`

- [ ] **Step 3: Add `_team_score()` and `optimize_teams()` to `balance.py`**

Append to `pyball/application/meetup/balance.py`:

```python
def _team_score(
    team: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
    max_pair_wins: int,
) -> float:
    """Compute the aggregate strength score for a team."""
    total = sum(player_scores.get(pid, 0.5) for pid in team)
    if max_pair_wins == 0:
        return total
    for pid_a, pid_b in itertools.combinations(team, 2):
        key = tuple(sorted([str(pid_a.value), str(pid_b.value)]))
        pair_wins = winning_counts.get(key, 0)
        total += (pair_wins / max_pair_wins) * _PAIR_WEIGHT
    return total


def optimize_teams(
    player_ids: list[PlayerId],
    player_scores: dict[PlayerId, float],
    winning_counts: dict[tuple[str, str], int],
) -> tuple[list[PlayerId], list[PlayerId]]:
    """Assign players to two balanced teams using local-search optimization.

    Starts from a random split and iterates _ITERATIONS times, accepting swaps
    that reduce the score difference between teams. Each call starts from a
    fresh random state, producing varied but balanced results.
    """
    if len(player_ids) < 2:
        raise ValueError("Need at least 2 players to create teams")

    players = list(player_ids)
    random.shuffle(players)
    mid = len(players) // 2
    team_a: list[PlayerId] = players[:mid]
    team_b: list[PlayerId] = players[mid:]

    max_pair_wins = max(winning_counts.values(), default=0)

    for _ in range(_ITERATIONS):
        i = random.randrange(len(team_a))
        j = random.randrange(len(team_b))

        current_diff = abs(
            _team_score(team_a, player_scores, winning_counts, max_pair_wins)
            - _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        )

        team_a[i], team_b[j] = team_b[j], team_a[i]

        new_diff = abs(
            _team_score(team_a, player_scores, winning_counts, max_pair_wins)
            - _team_score(team_b, player_scores, winning_counts, max_pair_wins)
        )

        if new_diff > current_diff:
            team_a[i], team_b[j] = team_b[j], team_a[i]

    return team_a, team_b
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -e test -- tests/unit/application/test_balance.py -v
```

Expected: all PASS

- [ ] **Step 5: Run lint to verify balance.py is clean**

```bash
nox -e lint
```

Expected: pylint 10.00/10, mypy clean, no formatting issues.
Fix any issues before continuing.

- [ ] **Step 6: Commit**

```bash
git add pyball/application/meetup/balance.py tests/unit/application/test_balance.py
git commit -m "feat: add optimize_teams to balance module"
```

---

## Task 5: Update `CreateTeams` use case and tests

**Files:**
- Modify: `pyball/application/meetup/create_teams.py`
- Modify: `pyball/domain/meetup/models.py` (remove `create_random_teams`)
- Modify: `tests/unit/application/test_meetup_use_cases.py`

- [ ] **Step 1: Write the new tests first**

In `tests/unit/application/test_meetup_use_cases.py`, replace the entire `TestCreateTeams` class with:

```python
class TestCreateTeams:
    """Tests for CreateTeams use case."""

    def test_create_teams_success(self):
        """Creating teams for a meetup with 2 players produces two teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        result = use_case.execute("2024/01/15 20:00")

        assert result.teams is not None
        assert len(result.teams) == 2

    def test_create_teams_meetup_not_found(self):
        """Creating teams when the meetup does not exist raises MeetupNotFoundError."""
        meetup_repo = FakeMeetupRepository()
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute("2024/01/15 20:00")

    def test_create_teams_not_enough_players(self):
        """Creating teams with fewer than 2 players raises ValueError."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(ValueError, match="Need at least 2"):
            use_case.execute("2024/01/15 20:00")

    def test_create_teams_all_players_assigned(self):
        """All meetup players appear in exactly one team after create_teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player_ids = [PlayerId.generate() for _ in range(6)]
        for pid in player_ids:
            meetup.add_player(pid)
        meetup_repo.save(meetup)

        result = CreateTeams(meetup_repo).execute("2024/01/15 20:00")

        all_assigned = list(result.teams[0].players) + list(result.teams[1].players)
        assert sorted(str(p.value) for p in all_assigned) == sorted(
            str(p.value) for p in player_ids
        )

    def test_create_teams_produces_varied_results(self):
        """Repeated calls on the same meetup produce more than one distinct assignment."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        for _ in range(6):
            meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        compositions = set()
        for _ in range(30):
            result = use_case.execute("2024/01/15 20:00")
            compositions.add(frozenset(result.teams[0].players))

        assert len(compositions) > 1
```

- [ ] **Step 2: Run tests to verify the new tests fail (or pass for unchanged ones)**

```bash
nox -e test -- tests/unit/application/test_meetup_use_cases.py::TestCreateTeams -v
```

Expected: `test_create_teams_all_players_assigned` and `test_create_teams_produces_varied_results` FAIL with `AssertionError` (varied results test fails because current impl is still random without variety guarantee).

- [ ] **Step 3: Rewrite `create_teams.py`**

Replace the entire content of `pyball/application/meetup/create_teams.py`:

```python
"""Create balanced teams use case."""

from datetime import date, datetime

from pyball.application.meetup.balance import (
    compute_player_scores,
    extract_winning_counts,
    optimize_teams,
)
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.exceptions import MeetupError


def _season_start(today: date) -> date:
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)


class CreateTeams:
    """Use case for creating history-aware balanced teams."""

    def __init__(self, meetup_repository: MeetupRepository):
        """Initialize with a meetup repository."""
        self.meetup_repository = meetup_repository

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

        player_scores = compute_player_scores(meetup.players, season_meetups, finished)
        winning_counts = extract_winning_counts(finished)
        team_a_ids, team_b_ids = optimize_teams(meetup.players, player_scores, winning_counts)

        meetup.set_teams([Team.create("A", team_a_ids), Team.create("B", team_b_ids)])
        self.meetup_repository.save(meetup)
        return meetup


class InvalidMeetupDateError(ValueError, MeetupError):
    """Raised when meetup date format is invalid."""
```

- [ ] **Step 4: Remove `create_random_teams()` from `Meetup`**

In `pyball/domain/meetup/models.py`, delete the `create_random_teams` method (lines 63–75):

```python
    def create_random_teams(self) -> None:
        """Create two randomly-assigned teams from the players."""
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to create teams")

        players_copy = list(self.players)
        _random.shuffle(players_copy)

        mid = len(players_copy) // 2
        self.teams = [
            Team.create("A", players_copy[:mid]),
            Team.create("B", players_copy[mid:]),
        ]
```

Also remove the now-unused `import random as _random` at the top of `models.py` (line 5).

- [ ] **Step 5: Run the full test suite**

```bash
nox -e test
```

Expected: all tests PASS

- [ ] **Step 6: Run lint**

```bash
nox -e lint
```

Expected: pylint 10.00/10, mypy clean. Fix any issues before continuing.

- [ ] **Step 7: Commit**

```bash
git add pyball/application/meetup/create_teams.py pyball/domain/meetup/models.py tests/unit/application/test_meetup_use_cases.py
git commit -m "feat: replace random team creation with history-aware balanced algorithm"
```
