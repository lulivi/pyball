# Match Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the admin to start a match via Telegram, record goals and assists on a web kiosk, and save the result back to the backend which closes the callup messages.

**Architecture:** Extend the `Meetup` domain model with `MatchResult` and `GoalEvent` value objects. Add two application use cases (`StartMatch`, `FinishMatch`). Run a FastAPI server alongside the Telegram bot under the same asyncio loop; it serves the static web kiosk and exposes `POST /api/match/finish`. Network security is handled by Tailscale (no auth tokens required).

**Tech Stack:** Python 3.12, python-telegram-bot 22, FastAPI, uvicorn, pytest, nox

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `pyball/domain/meetup/models.py` | Add `GoalEvent`, `MatchResult`, `Meetup.set_result()`, `Meetup.is_closed()` |
| Modify | `pyball/infrastructure/persistence/meetup_repository.py` | Serialize/deserialize `result` field |
| Modify | `pyball/settings.py` | Add `base_url` to `PyballSettings` |
| Modify | `example.config.toml` | Document new `base_url` field |
| Create | `pyball/application/meetup/start_match.py` | `StartMatch` use case |
| Create | `pyball/application/meetup/finish_match.py` | `FinishMatch` use case + `MeetupAlreadyClosedError` |
| Modify | `pyball/application/meetup/__init__.py` | Export new use cases |
| Modify | `pyball/application/container.py` | Add `start_match()` and `finish_match()` factory methods |
| Modify | `pyball/bot/formatters.py` | Add result branch to `format_main_message` / `format_subs_message` |
| Create | `pyball/infrastructure/http/__init__.py` | Package marker |
| Create | `pyball/infrastructure/http/app.py` | FastAPI app factory + endpoint + Pydantic models |
| Modify | `pyball/__main__.py` | Async main: run bot + uvicorn under same event loop |
| Modify | `pyball/bot/handlers/meetup.py` | Add `/start_match` handler + `close_match_messages()` helper |
| Modify | `static/index.html` | Read teams from URL params; remove `fetchLineups()`; send `meetup_date` in POST |
| Modify | `pyproject.toml` | Add `fastapi` and `uvicorn[standard]` dependencies |
| Modify | `tests/unit/domain/test_meetup.py` | Tests for new domain model additions |
| Modify | `tests/unit/application/test_meetup_use_cases.py` | Tests for `StartMatch` and `FinishMatch` |
| Modify | `tests/integration/test_persistence_meetup_repository.py` | Round-trip test for `result` field |
| Modify | `tests/unit/bot/test_formatters.py` | Tests for result branch in formatters |

---

### Task 1: Domain model — GoalEvent, MatchResult, Meetup.set_result / is_closed

**Files:**
- Modify: `pyball/domain/meetup/models.py`
- Modify: `tests/unit/domain/test_meetup.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/domain/test_meetup.py`:

```python
from datetime import datetime

import pytest

from pyball.domain.meetup.models import GoalEvent, Meetup, MatchResult
from pyball.domain.player.models import PlayerId


class TestGoalEvent:
    """Tests for GoalEvent value object."""

    def test_goal_event_with_assistant(self):
        """A goal event stores scorer, optional assistant, team and timestamp."""
        scorer = PlayerId.generate()
        assistant = PlayerId.generate()
        ts = datetime(2026, 4, 12, 20, 15)
        event = GoalEvent(scorer_id=scorer, assistant_id=assistant, team="A", timestamp=ts)
        assert event.scorer_id == scorer
        assert event.assistant_id == assistant
        assert event.team == "A"
        assert event.timestamp == ts

    def test_goal_event_without_assistant(self):
        """A goal event may have no assistant."""
        scorer = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer, assistant_id=None, team="B", timestamp=datetime(2026, 4, 12, 20, 5)
        )
        assert event.assistant_id is None


class TestMatchResult:
    """Tests for MatchResult value object."""

    def test_match_result_stores_score_and_events(self):
        """MatchResult holds the final score and goal events."""
        scorer = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer,
            assistant_id=None,
            team="A",
            timestamp=datetime(2026, 4, 12, 20, 5),
        )
        result = MatchResult(score_a=1, score_b=0, events=(event,))
        assert result.score_a == 1
        assert result.score_b == 0
        assert len(result.events) == 1


class TestMeetupResult:
    """Tests for Meetup.set_result and is_closed."""

    def _meetup_with_teams(self):
        from pyball.domain.meetup.models import Team

        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        return meetup

    def test_is_closed_false_by_default(self):
        """A new meetup is not closed."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        assert not meetup.is_closed()

    def test_set_result_closes_meetup(self):
        """Setting a result marks the meetup as closed."""
        meetup = self._meetup_with_teams()
        result = MatchResult(score_a=3, score_b=2, events=())
        meetup.set_result(result)
        assert meetup.is_closed()
        assert meetup.result == result

    def test_set_result_requires_teams(self):
        """set_result raises ValueError if teams have not been created."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        result = MatchResult(score_a=1, score_b=0, events=())
        with pytest.raises(ValueError, match="Cannot set result without teams"):
            meetup.set_result(result)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -s test -- tests/unit/domain/test_meetup.py -k "GoalEvent or MatchResult or MeetupResult" -v
```

Expected: `ImportError` or `AttributeError` — `GoalEvent`, `MatchResult` not defined yet.

- [ ] **Step 3: Add GoalEvent and MatchResult to models.py, extend Meetup**

In `pyball/domain/meetup/models.py`, after the existing imports add:

```python
@dataclass(frozen=True)
class GoalEvent(ValueObject):
    """Value object representing a single goal event."""

    scorer_id: PlayerId
    assistant_id: PlayerId | None
    team: str
    timestamp: datetime


@dataclass(frozen=True)
class MatchResult(ValueObject):
    """Value object representing the final result of a match."""

    score_a: int
    score_b: int
    events: tuple[GoalEvent, ...]
```

And in the `Meetup` dataclass add after `teams`:

```python
    result: MatchResult | None = None

    def set_result(self, result: MatchResult) -> None:
        """Attach the match result. Requires teams to exist."""
        if self.teams is None:
            raise ValueError("Cannot set result without teams")
        self.result = result

    def is_closed(self) -> bool:
        """True if the match result has been recorded."""
        return self.result is not None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -s test -- tests/unit/domain/test_meetup.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pyball/domain/meetup/models.py tests/unit/domain/test_meetup.py
git commit -m "feat(domain): add GoalEvent, MatchResult, Meetup.set_result and is_closed"
```

---

### Task 2: JSON repository — serialize and deserialize result

**Files:**
- Modify: `pyball/infrastructure/persistence/meetup_repository.py`
- Modify: `tests/integration/test_persistence_meetup_repository.py`

- [ ] **Step 1: Write failing test**

Add to `tests/integration/test_persistence_meetup_repository.py`:

```python
from datetime import datetime

from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId


class TestJsonMeetupRepositoryResult:
    """Integration tests for MatchResult persistence."""

    def setup_method(self):
        import shutil
        import tempfile
        from pathlib import Path

        from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository

        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_save_and_load_meetup_with_result(self):
        """A meetup with a MatchResult round-trips through JSON correctly."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        scorer = PlayerId.generate()
        assistant = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer,
            assistant_id=assistant,
            team="A",
            timestamp=datetime(2026, 4, 12, 20, 15),
        )
        result = MatchResult(score_a=2, score_b=1, events=(event,))
        meetup.set_result(result)

        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)

        assert loaded is not None
        assert loaded.result is not None
        assert loaded.result.score_a == 2
        assert loaded.result.score_b == 1
        assert len(loaded.result.events) == 1
        assert loaded.result.events[0].scorer_id == scorer
        assert loaded.result.events[0].assistant_id == assistant
        assert loaded.result.events[0].team == "A"
        assert loaded.result.events[0].timestamp == datetime(2026, 4, 12, 20, 15)

    def test_save_and_load_meetup_without_result(self):
        """A meetup with no result loads with result=None."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)
        assert loaded is not None
        assert loaded.result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -s test -- tests/integration/test_persistence_meetup_repository.py::TestJsonMeetupRepositoryResult -v
```

Expected: FAIL — the loaded meetup has `result=None` even when one was set.

- [ ] **Step 3: Update _dict_to_meetup to deserialize result**

In `pyball/infrastructure/persistence/meetup_repository.py`, update the import at the top:

```python
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, MeetupId, Team
```

Then replace the `_dict_to_meetup` method with:

```python
    def _dict_to_meetup(self, data: dict) -> Meetup:
        teams = None
        if data.get("teams"):
            teams = [
                Team.create(t["name"], [PlayerId(UUID(p)) for p in t["players"]])
                for t in data["teams"]
            ]
        result = None
        if data.get("result"):
            r = data["result"]
            events = tuple(
                GoalEvent(
                    scorer_id=PlayerId(UUID(e["scorer_id"])),
                    assistant_id=PlayerId(UUID(e["assistant_id"])) if e.get("assistant_id") else None,
                    team=e["team"],
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                )
                for e in r.get("events", [])
            )
            result = MatchResult(
                score_a=r["score_a"],
                score_b=r["score_b"],
                events=events,
            )
        return Meetup(
            id=MeetupId(UUID(data["id"])),
            date=datetime.fromisoformat(data["date"]),
            location=data.get("location", "Parque Central"),
            players=[PlayerId(UUID(p)) for p in data.get("players", [])],
            teams=teams,
            result=result,
        )
```

- [ ] **Step 4: Update _write to serialize result**

Replace the `_write` method with:

```python
    def _write(self, meetup: Meetup) -> None:
        file_path = self._get_file_path(meetup)
        teams_data = None
        if meetup.teams:
            teams_data = [
                {"name": t.name, "players": [str(p.value) for p in t.players]}
                for t in meetup.teams
            ]
        result_data = None
        if meetup.result:
            result_data = {
                "score_a": meetup.result.score_a,
                "score_b": meetup.result.score_b,
                "events": [
                    {
                        "scorer_id": str(e.scorer_id.value),
                        "assistant_id": str(e.assistant_id.value) if e.assistant_id else None,
                        "team": e.team,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in meetup.result.events
                ],
            }
        data = {
            "id": str(meetup.id.value),
            "date": meetup.date.isoformat(),
            "location": meetup.location,
            "players": [str(p.value) for p in meetup.players],
            "teams": teams_data,
            "result": result_data,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
```

- [ ] **Step 5: Run all tests to verify they pass**

```bash
nox -s test -- tests/integration/test_persistence_meetup_repository.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pyball/infrastructure/persistence/meetup_repository.py tests/integration/test_persistence_meetup_repository.py
git commit -m "feat(persistence): serialize and deserialize MatchResult in JSON meetup repository"
```

---

### Task 3: Settings — add base_url

**Files:**
- Modify: `pyball/settings.py`
- Modify: `example.config.toml`

- [ ] **Step 1: Add base_url to PyballSettings**

In `pyball/settings.py`, update the `PyballSettings` dataclass:

```python
@dataclass
class PyballSettings:
    """PyBall-specific configuration."""

    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
    base_url: str = "http://localhost:8000"
```

- [ ] **Step 2: Wire base_url in load_settings**

In `load_settings()`, update the `pyball` block:

```python
    pyball = PyballSettings(
        location=_get_env_override("pyball", "location", pyball_cfg.get("location", "")),
        default_week_day=_get_env_override(
            "pyball", "default_week_day", pyball_cfg.get("default_week_day", "wednesday")
        ),
        default_hour=_get_env_override(
            "pyball", "default_hour", pyball_cfg.get("default_hour", "20:00")
        ),
        base_url=_get_env_override(
            "pyball", "base_url", pyball_cfg.get("base_url", "http://localhost:8000")
        ),
    )
```

- [ ] **Step 3: Document base_url in example.config.toml**

Add after `default_hour` in `example.config.toml`:

```toml
# Optional: Base URL used to generate match links (use Tailscale hostname)
# Override with PYBALL_PYBALL_BASE_URL
base_url = "http://pyball:8000"
```

- [ ] **Step 4: Run existing settings tests**

```bash
nox -s test -- tests/unit/test_settings.py -v
```

Expected: all PASS (base_url defaults to `http://localhost:8000`).

- [ ] **Step 5: Commit**

```bash
git add pyball/settings.py example.config.toml
git commit -m "feat(settings): add base_url for match link generation"
```

---

### Task 4: StartMatch use case

**Files:**
- Create: `pyball/application/meetup/start_match.py`
- Modify: `tests/unit/application/test_meetup_use_cases.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/application/test_meetup_use_cases.py` (reuse the existing `FakeMeetupRepository` and `FakePlayerRepository` already defined in that file):

```python
from pyball.application.meetup.start_match import StartMatch, MeetupHasNoTeamsError
from pyball.domain.meetup.models import Meetup, Team


class TestStartMatch:
    """Tests for StartMatch use case."""

    def setup_method(self):
        self.meetup_repo = FakeMeetupRepository()
        self.player_repo = FakePlayerRepository()
        self.use_case = StartMatch(self.meetup_repo, self.player_repo, "http://pyball:8000")

    def _add_players_and_teams(self, meetup):
        from pyball.domain.player.models import Player

        p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
        p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
        self.player_repo.players.append(p1)
        self.player_repo.players.append(p2)
        meetup.teams = [Team.create("A", [p1.id]), Team.create("B", [p2.id])]
        self.meetup_repo.save(meetup)
        return p1, p2

    def test_returns_url_with_teams_and_date(self):
        """StartMatch returns a URL containing date and team names."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1, p2 = self._add_players_and_teams(meetup)

        url = self.use_case.execute("2026-04-12 20:00")

        assert "2026-04-12T20%3A00" in url or "2026-04-12T20:00" in url
        assert "Dani" in url
        assert "Rafa" in url
        assert url.startswith("http://pyball:8000")

    def test_raises_if_meetup_not_found(self):
        """StartMatch raises MeetupNotFoundError if no meetup exists on that date."""
        from pyball.domain.meetup.errors import MeetupNotFoundError

        with pytest.raises(MeetupNotFoundError):
            self.use_case.execute("2026-04-12 20:00")

    def test_raises_if_no_teams(self):
        """StartMatch raises MeetupHasNoTeamsError if teams have not been created."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.meetup_repo.save(meetup)

        with pytest.raises(MeetupHasNoTeamsError):
            self.use_case.execute("2026-04-12 20:00")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -s test -- tests/unit/application/test_meetup_use_cases.py::TestStartMatch -v
```

Expected: `ImportError` — `start_match` module does not exist.

- [ ] **Step 3: Create start_match.py**

Create `pyball/application/meetup/start_match.py`:

```python
"""Start match use case."""

import urllib.parse

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.exceptions import MeetupError


class MeetupHasNoTeamsError(MeetupError):
    """Raised when trying to start a match without teams."""


class StartMatch:
    """Use case for generating a match tracking URL."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
        base_url: str,
    ):
        """Initialize with repositories and the base URL."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository
        self.base_url = base_url

    def execute(self, date_str: str) -> str:
        """Generate the match tracking URL for the given meetup date.

        Args:
            date_str: Meetup date in 'YYYY-MM-DD HH:MM' format.

        Returns:
            URL string with encoded team names and date.

        Raises:
            MeetupNotFoundError: If no meetup exists on that date.
            MeetupHasNoTeamsError: If the meetup has no teams yet.
        """
        try:
            meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("Invalid date format. Use: YYYY-MM-DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")

        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        team_a_names = [player_names[str(pid.value)] for pid in meetup.teams[0].players]
        team_b_names = [player_names[str(pid.value)] for pid in meetup.teams[1].players]

        params = urllib.parse.urlencode(
            {
                "date": meetup_date.strftime("%Y-%m-%dT%H:%M"),
                "teamA": ",".join(team_a_names),
                "teamB": ",".join(team_b_names),
            }
        )
        return f"{self.base_url}/?{params}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -s test -- tests/unit/application/test_meetup_use_cases.py::TestStartMatch -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/start_match.py tests/unit/application/test_meetup_use_cases.py
git commit -m "feat(application): add StartMatch use case"
```

---

### Task 5: FinishMatch use case

**Files:**
- Create: `pyball/application/meetup/finish_match.py`
- Modify: `tests/unit/application/test_meetup_use_cases.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/application/test_meetup_use_cases.py`:

```python
from pyball.application.meetup.finish_match import FinishMatch, MeetupAlreadyClosedError
from pyball.domain.meetup.models import Meetup, MatchResult, Team


class TestFinishMatch:
    """Tests for FinishMatch use case."""

    def setup_method(self):
        self.meetup_repo = FakeMeetupRepository()
        self.player_repo = FakePlayerRepository()
        self.use_case = FinishMatch(self.meetup_repo, self.player_repo)

    def _meetup_with_teams(self):
        from pyball.domain.player.models import Player

        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
        p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
        self.player_repo.players.extend([p1, p2])
        meetup.teams = [Team.create("A", [p1.id]), Team.create("B", [p2.id])]
        self.meetup_repo.save(meetup)
        return meetup, p1, p2

    def test_saves_result_with_resolved_player_ids(self):
        """FinishMatch resolves player names and persists MatchResult."""
        meetup, p1, p2 = self._meetup_with_teams()

        events = [
            {
                "scorer": "Dani",
                "assistant": "Rafa",
                "team": "A",
                "timestamp": "2026-04-12T20:15:00",
            }
        ]
        self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})

        saved = self.meetup_repo.find_by_date(datetime(2026, 4, 12).date())
        assert saved is not None
        assert saved.is_closed()
        assert saved.result.score_a == 1
        assert saved.result.score_b == 0
        assert len(saved.result.events) == 1
        assert saved.result.events[0].scorer_id == p1.id
        assert saved.result.events[0].assistant_id == p2.id

    def test_goal_without_assistant(self):
        """An event with assistant=None stores assistant_id=None."""
        meetup, p1, _ = self._meetup_with_teams()

        events = [
            {
                "scorer": "Dani",
                "assistant": None,
                "team": "A",
                "timestamp": "2026-04-12T20:05:00",
            }
        ]
        self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})

        saved = self.meetup_repo.find_by_date(datetime(2026, 4, 12).date())
        assert saved.result.events[0].assistant_id is None

    def test_raises_if_meetup_not_found(self):
        """FinishMatch raises MeetupNotFoundError for unknown dates."""
        from pyball.domain.meetup.errors import MeetupNotFoundError

        with pytest.raises(MeetupNotFoundError):
            self.use_case.execute("2026-04-12 20:00", [], {"A": 0, "B": 0})

    def test_raises_if_already_closed(self):
        """FinishMatch raises MeetupAlreadyClosedError if result already set."""
        meetup, _, _ = self._meetup_with_teams()
        result = MatchResult(score_a=1, score_b=0, events=())
        meetup.set_result(result)
        self.meetup_repo.save(meetup)

        with pytest.raises(MeetupAlreadyClosedError):
            self.use_case.execute("2026-04-12 20:00", [], {"A": 1, "B": 0})

    def test_raises_if_player_not_found(self):
        """FinishMatch raises ValueError if a player name cannot be resolved."""
        self._meetup_with_teams()

        events = [
            {
                "scorer": "Unknown",
                "assistant": None,
                "team": "A",
                "timestamp": "2026-04-12T20:00:00",
            }
        ]
        with pytest.raises(ValueError, match="Player not found"):
            self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -s test -- tests/unit/application/test_meetup_use_cases.py::TestFinishMatch -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create finish_match.py**

Create `pyball/application/meetup/finish_match.py`:

```python
"""Finish match use case."""

from datetime import datetime

from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import GoalEvent, MatchResult
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.exceptions import MeetupError


class MeetupAlreadyClosedError(MeetupError):
    """Raised when trying to finish a match that already has a result."""


class FinishMatch:
    """Use case for recording the match result."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ):
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(
        self,
        date_str: str,
        events: list[dict],
        final_score: dict[str, int],
    ):
        """Save the match result for the given meetup.

        Args:
            date_str: Meetup date in 'YYYY-MM-DD HH:MM' format.
            events: List of goal event dicts with keys:
                    scorer (str), assistant (str|None), team (str), timestamp (str ISO).
            final_score: Dict with keys 'A' and 'B' mapping to int scores.

        Returns:
            The updated Meetup.

        Raises:
            MeetupNotFoundError: If no meetup on that date.
            MeetupAlreadyClosedError: If the meetup already has a result.
            ValueError: If a player name cannot be fuzzy-matched.
        """
        try:
            meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("Invalid date format. Use: YYYY-MM-DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.is_closed():
            raise MeetupAlreadyClosedError(f"Match on {date_str} is already closed.")

        all_players = self.player_repository.find_all()

        goal_events = []
        for e in events:
            scorer_match = fuzzy_match_player(e["scorer"], all_players)
            assistant_id = None
            if e.get("assistant"):
                assistant_match = fuzzy_match_player(e["assistant"], all_players)
                assistant_id = assistant_match.player_id
            goal_events.append(
                GoalEvent(
                    scorer_id=scorer_match.player_id,
                    assistant_id=assistant_id,
                    team=e["team"],
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                )
            )

        result = MatchResult(
            score_a=final_score["A"],
            score_b=final_score["B"],
            events=tuple(goal_events),
        )
        meetup.set_result(result)
        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
nox -s test -- tests/unit/application/test_meetup_use_cases.py::TestFinishMatch -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/finish_match.py tests/unit/application/test_meetup_use_cases.py
git commit -m "feat(application): add FinishMatch use case"
```

---

### Task 6: Wire up — exports and container

**Files:**
- Modify: `pyball/application/meetup/__init__.py`
- Modify: `pyball/application/container.py`

- [ ] **Step 1: Update meetup __init__ exports**

Replace `pyball/application/meetup/__init__.py` with:

```python
"""Meetup use cases."""

from pyball.application.meetup.add_player import AddPlayerToMeetup
from pyball.application.meetup.create_meetup import CreateMeetup, DuplicateMeetupError
from pyball.application.meetup.create_teams import CreateTeams, InvalidMeetupDateError
from pyball.application.meetup.finish_match import FinishMatch, MeetupAlreadyClosedError
from pyball.application.meetup.remove_player import RemovePlayerFromMeetup
from pyball.application.meetup.start_match import MeetupHasNoTeamsError, StartMatch

__all__ = [
    "CreateMeetup",
    "DuplicateMeetupError",
    "AddPlayerToMeetup",
    "RemovePlayerFromMeetup",
    "CreateTeams",
    "InvalidMeetupDateError",
    "StartMatch",
    "MeetupHasNoTeamsError",
    "FinishMatch",
    "MeetupAlreadyClosedError",
]
```

- [ ] **Step 2: Add factory methods to Container**

In `pyball/application/container.py`, update the import block to add the new use cases:

```python
from pyball.application.meetup import (
    AddPlayerToMeetup,
    CreateMeetup,
    CreateTeams,
    FinishMatch,
    RemovePlayerFromMeetup,
    StartMatch,
)
```

Then add these two methods to the `Container` class:

```python
    def start_match(self) -> StartMatch:
        """Create a new StartMatch use case."""
        return StartMatch(
            self.meetup_repository,
            self.player_repository,
            self._settings.pyball.base_url,
        )

    def finish_match(self) -> FinishMatch:
        """Create a new FinishMatch use case."""
        return FinishMatch(self.meetup_repository, self.player_repository)
```

- [ ] **Step 3: Run full test suite to confirm nothing broke**

```bash
nox -s test
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add pyball/application/meetup/__init__.py pyball/application/container.py
git commit -m "feat(container): wire StartMatch and FinishMatch into DI container"
```

---

### Task 7: Formatters — result branch

**Files:**
- Modify: `pyball/bot/formatters.py`
- Modify: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/bot/test_formatters.py`:

```python
from datetime import datetime

from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId


def test_format_main_message_with_result_shows_score():
    """When meetup has a result, format_main_message shows score next to team name."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    event = GoalEvent(
        scorer_id=p1, assistant_id=None, team="A", timestamp=datetime(2026, 4, 12, 20, 15)
    )
    meetup.set_result(MatchResult(score_a=3, score_b=1, events=(event,)))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_main_message(meetup, player_names)

    assert "A (3)" in text or "A \\(3\\)" in text
    assert "B (1)" in text or "B \\(1\\)" in text
    assert "Dani" in text
    assert "Rafa" in text


def test_format_subs_message_with_result_shows_score():
    """When meetup has a result, format_subs_message shows score next to team name."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    meetup.set_result(MatchResult(score_a=2, score_b=0, events=()))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    player_groups = {str(p1.value): "regular", str(p2.value): "regular"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "2" in text
    assert "0" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
nox -s test -- tests/unit/bot/test_formatters.py -k "result" -v
```

Expected: FAIL — formatters don't have a result branch yet.

- [ ] **Step 3: Update format_main_message**

In `pyball/bot/formatters.py`, replace the `else:` branch in `format_main_message` (the teams section) with:

```python
    else:
        lines.append("*Equipos:*")
        for i, team in enumerate(meetup.teams):
            score = None
            if meetup.result is not None:
                score = meetup.result.score_a if i == 0 else meetup.result.score_b
            header = (
                rf"*{team.name} \({score}\):*"
                if score is not None
                else f"\n*{team.name}:*"
            )
            lines.append(header)
            for player in team.players:
                name = _escape_mdv2(player_names.get(str(player.value), "Unknown"))
                lines.append(rf"\- {name}")
```

- [ ] **Step 4: Update format_subs_message**

In `pyball/bot/formatters.py`, update `format_subs_message` to add the result score when present. Replace the header line:

```python
    lines = [rf"*Convocatoria* {date_str} \- Suplentes"]
```

with:

```python
    if meetup.result is not None:
        score_line = rf"{meetup.result.score_a} \- {meetup.result.score_b}"
        lines = [rf"*Convocatoria* {date_str} \- Suplentes \| {score_line}"]
    else:
        lines = [rf"*Convocatoria* {date_str} \- Suplentes"]
```

- [ ] **Step 5: Run all formatter tests**

```bash
nox -s test -- tests/unit/bot/test_formatters.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat(formatters): show final score in callup messages after match result"
```

---

### Task 8: FastAPI HTTP app

**Files:**
- Modify: `pyproject.toml`
- Create: `pyball/infrastructure/http/__init__.py`
- Create: `pyball/infrastructure/http/app.py`

- [ ] **Step 1: Add fastapi and uvicorn to dependencies**

In `pyproject.toml`, add to `[tool.poetry.dependencies]`:

```toml
fastapi = ">=0.110"
uvicorn = {extras = ["standard"], version = ">=0.29"}
```

Then install:

```bash
poetry install
```

- [ ] **Step 2: Create package marker**

Create `pyball/infrastructure/http/__init__.py`:

```python
"""HTTP infrastructure package."""
```

- [ ] **Step 3: Create the FastAPI app factory**

Create `pyball/infrastructure/http/app.py`:

```python
"""FastAPI application factory."""

import logging

from pathlib import Path
from typing import TYPE_CHECKING

import telegram

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pyball.application.meetup.finish_match import MeetupAlreadyClosedError
from pyball.domain.meetup.errors import MeetupNotFoundError

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.settings import Settings

logger = logging.getLogger(__name__)


class GoalEventInput(BaseModel):
    """Pydantic model for a single goal event from the frontend."""

    scorer: str
    assistant: str | None
    team: str
    timestamp: str


class FinalScore(BaseModel):
    """Pydantic model for the final score."""

    A: int
    B: int


class FinishMatchInput(BaseModel):
    """Pydantic model for the POST /api/match/finish request body."""

    meetup_date: str
    events: list[GoalEventInput]
    finalScore: FinalScore


def create_app(
    container: "Container",
    bot: telegram.Bot,
    settings: "Settings",
    static_dir: Path = Path("static"),
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        container: DI container with repositories and use cases.
        bot: Telegram Bot instance for editing messages after match.
        settings: Application settings (for message store path and chat config).
        static_dir: Path to the static files directory.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="PyBall Match API")

    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and update Telegram callup messages."""
        use_case = container.finish_match()
        events = [e.model_dump() for e in body.events]
        try:
            meetup = use_case.execute(body.meetup_date, events, {"A": body.finalScore.A, "B": body.finalScore.B})
        except MeetupNotFoundError:
            raise HTTPException(status_code=404, detail="Meetup not found")
        except MeetupAlreadyClosedError:
            raise HTTPException(status_code=409, detail="Match already closed")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        all_players = container.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}
        player_groups = {str(p.id.value): p.group for p in all_players}

        from pyball.bot.handlers.meetup import close_match_messages
        from pyball.infrastructure.telegram import TelegramMessageStore

        message_store = TelegramMessageStore(settings.paths.bot_messages_file)
        await close_match_messages(bot, settings, message_store, meetup, player_names, player_groups)

        return {
            "meetup_date": body.meetup_date,
            "score_a": meetup.result.score_a,
            "score_b": meetup.result.score_b,
        }

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
```

- [ ] **Step 4: Run the existing test suite to make sure imports are clean**

```bash
nox -s test
```

Expected: all PASS (no import side effects).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pyball/infrastructure/http/ poetry.lock
git commit -m "feat(http): add FastAPI app factory with POST /api/match/finish endpoint"
```

---

### Task 9: Refactor __main__.py — async event loop

**Files:**
- Modify: `pyball/__main__.py`

- [ ] **Step 1: Rewrite __main__.py**

Replace the entire content of `pyball/__main__.py` with:

```python
"""Bot main file."""

import asyncio
import logging

import uvicorn

from pyball import __version__
from pyball.application.container import Container
from pyball.bot import create_application
from pyball.bot.handlers import (
    setup_general_handlers,
    setup_meetup_handlers,
    setup_player_handlers,
)
from pyball.infrastructure.http.app import create_app
from pyball.settings import load_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_startup_info() -> None:
    """Log startup information."""
    logger.info("*" * 40)
    logger.info("PyBall v%s", __version__)
    logger.info("*" * 40)


async def main_async() -> None:
    """Start the bot and HTTP server under the same asyncio event loop."""
    log_startup_info()

    settings = load_settings()
    container = Container()
    application = create_application()
    application.bot_data["container"] = container
    application.bot_data["settings"] = settings

    setup_player_handlers(application)
    setup_meetup_handlers(application)
    setup_general_handlers(application)

    fastapi_app = create_app(container, application.bot, settings)
    server_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(server_config)

    async with application:
        await application.start()
        await application.updater.start_polling()
        logger.info("Bot polling started")
        await server.serve()
        logger.info("HTTP server stopped — shutting down bot")
        await application.updater.stop()
        await application.stop()


def main() -> None:
    """Entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the app boots (manual smoke test)**

```bash
poetry run pyball
```

Expected: logs show bot polling started and uvicorn listening on port 8000. Press Ctrl+C to stop. Confirm both stop cleanly.

- [ ] **Step 3: Commit**

```bash
git add pyball/__main__.py
git commit -m "refactor(__main__): run bot and FastAPI server under shared asyncio event loop"
```

---

### Task 10: Bot handler — /start_match and close_match_messages

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`

- [ ] **Step 1: Add close_match_messages helper**

Add this async function to `pyball/bot/handlers/meetup.py` (before `setup_meetup_handlers`):

```python
async def close_match_messages(
    bot,
    settings,
    message_store,
    meetup,
    player_names: dict,
    player_groups: dict,
) -> None:
    """Edit callup messages to show final score and remove join/leave buttons.

    Args:
        bot: Telegram Bot instance.
        settings: Application settings with chat IDs and message store path.
        message_store: TelegramMessageStore to look up tracked message IDs.
        meetup: Meetup with result already set.
        player_names: Dict of str(UUID) -> player name.
        player_groups: Dict of str(UUID) -> player group.
    """
    date_key = meetup.date.strftime("%Y-%m-%dT%H:%M")

    regular_tracking = message_store.get_message(date_key, "regular")
    if regular_tracking:
        text = format_main_message(meetup, player_names)
        try:
            await bot.edit_message_text(
                chat_id=regular_tracking.chat_id,
                message_id=regular_tracking.message_id,
                text=text,
                reply_markup=None,
                parse_mode="MarkdownV2",
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit regulars message: %s", error)

    sub_tracking = message_store.get_message(date_key, "substitute")
    if sub_tracking:
        text = format_subs_message(meetup, player_names, player_groups)
        try:
            await bot.edit_message_text(
                chat_id=sub_tracking.chat_id,
                message_id=sub_tracking.message_id,
                text=text,
                reply_markup=None,
                parse_mode="MarkdownV2",
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit substitutes message: %s", error)
```

- [ ] **Step 2: Add /start_match handler**

Add this handler function to `pyball/bot/handlers/meetup.py`:

```python
@authorized
async def start_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start_match command — generate match URL and reply to admins only."""
    message = update.message
    if message is None:
        return

    args = context.args
    if not args or len(args) < 2:
        await message.reply_text("Usage: /start_match YYYY-MM-DD HH:MM")
        return

    date_str = " ".join(args)
    container: Container = context.bot_data["container"]

    try:
        url = container.start_match().execute(date_str)
        await message.reply_text(
            f"🔗 Enlace del partido:\n{url}",
            disable_web_page_preview=True,
        )
    except ValueError as error:
        await message.reply_text(str(error))
    except MeetupError as error:
        logger.error("Meetup error starting match: %s", error)
        await message.reply_text(str(error))
    except Exception as error:
        logger.exception("Error starting match: %s", error)
        await message.reply_text("An error occurred. Please try again.")
```

- [ ] **Step 3: Register the handler in setup_meetup_handlers**

Add this line inside `setup_meetup_handlers`:

```python
    application.add_handler(CommandHandler("start_match", start_match_handler))
```

- [ ] **Step 4: Ensure MeetupError is caught for MeetupHasNoTeamsError**

`MeetupHasNoTeamsError` already inherits from `MeetupError`, so the `except MeetupError` block in the handler catches it and shows the message to the admin. No extra handling needed.

- [ ] **Step 5: Run the test suite**

```bash
nox -s test
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pyball/bot/handlers/meetup.py
git commit -m "feat(bot): add /start_match handler and close_match_messages helper"
```

---

### Task 11: Frontend — read teams from URL, remove fetchLineups

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Update initializeApp to read from URL params**

In `static/index.html`, replace the entire `initializeApp` function with:

```js
async function initializeApp() {
    const savedState = localStorage.getItem('pyball_current_match');
    const savedTeams = localStorage.getItem('pyball_teams');

    if (savedState && savedTeams) {
        appState = JSON.parse(savedState);
        const teams = JSON.parse(savedTeams);
        teamA = teams.teamA;
        teamB = teams.teamB;
        meetupDate = teams.meetupDate;
        updateUI();
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const teamAParam = params.get('teamA');
    const teamBParam = params.get('teamB');
    meetupDate = params.get('date') || '';

    if (!teamAParam || !teamBParam) {
        document.getElementById('interaction-panel').innerHTML =
            "<p style='color:#f87171;'>❌ URL inválida. Genera el enlace con /start_match.</p>";
        document.getElementById('save-btn').disabled = true;
        return;
    }

    teamA = teamAParam.split(',');
    teamB = teamBParam.split(',');
    localStorage.setItem('pyball_teams', JSON.stringify({ teamA, teamB, meetupDate }));
    updateUI();
}
```

- [ ] **Step 2: Add meetupDate to app state and remove fetchLineups**

At the top of the `<script>` block, change the variable declarations:

```js
let teamA = [];
let teamB = [];
let meetupDate = '';
```

Delete the entire `fetchLineups` function.

- [ ] **Step 3: Add meetup_date to finishMatch POST body**

In the `finishMatch` function, replace the `body: JSON.stringify(...)` line with:

```js
body: JSON.stringify({
    meetup_date: meetupDate,
    events: [...appState.events].reverse(),
    finalScore: { A: appState.goalsA, B: appState.goalsB }
})
```

- [ ] **Step 4: Manual smoke test**

Open the following URL in a browser (with the server running via `poetry run pyball`):

```
http://localhost:8000/?date=2026-04-12T20:00&teamA=Dani,Rafa,Luis&teamB=Paco,Manu,Juanca
```

Expected: the scoreboard loads with the three players per team. Record a goal (select scorer then assister). Verify the event log updates and localStorage contains the state.

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat(frontend): load teams from URL params, remove fetchLineups, send meetup_date on finish"
```

---

### Task 12: Commit the design spec

Now that implementation is complete, commit the design document.

- [ ] **Step 1: Commit the spec**

```bash
git add docs/superpowers/specs/2026-04-11-match-tracking-design.md
git commit -m "docs: add match tracking design spec"
```
