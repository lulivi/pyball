# Post-Match Statistics Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every match finishes, automatically post two statistics images ("Esta temporada" / "Histórico") to the regulars Telegram group stats topic, each showing goal & assist rankings, points table, and top chemistry duos with rank-delta trend indicators.

**Architecture:** `ComputeStats` application use case aggregates data from both repositories into a `StatsReport` dataclass. `StatsImageRenderer` in `infrastructure/images/` renders two PNG images using `matplotlib`. The FastAPI `finish_match` endpoint launches a background asyncio task that calls both and sends the images to Telegram.

**Tech Stack:** Python 3.12, matplotlib ≥3.7, python-telegram-bot 22, FastAPI, pytest, nox

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `pyball/settings.py` | Rename `thread_id`→`meetups_thread_id`; add `RegularsChatSettings` with `stats_thread_id` |
| Modify | `example.config.toml` | Rename field; add `stats_thread_id` |
| Modify | `pyball/bot/handlers/meetup.py` | Update 3 `thread_id` refs to `meetups_thread_id` |
| Modify | `tests/unit/test_settings.py` | Tests for renamed field and new `RegularsChatSettings` |
| Create | `pyball/application/meetup/compute_stats.py` | `StatsReport` dataclasses + `ComputeStats` use case |
| Modify | `pyball/application/meetup/__init__.py` | Export `ComputeStats` and report types |
| Create | `tests/unit/application/test_compute_stats.py` | Unit tests for `ComputeStats` |
| Modify | `pyproject.toml` | Add `matplotlib` dependency |
| Create | `pyball/infrastructure/images/__init__.py` | Package marker |
| Create | `pyball/infrastructure/images/stats_renderer.py` | `StatsImageRenderer` |
| Create | `tests/unit/infrastructure/test_stats_renderer.py` | Smoke tests for `StatsImageRenderer` |
| Modify | `pyball/infrastructure/http/app.py` | Add `_post_match_stats` background task after match finish |

---

### Task 1: Settings — rename `thread_id` and add `RegularsChatSettings`

**Files:**
- Modify: `pyball/settings.py`
- Modify: `example.config.toml`
- Modify: `pyball/bot/handlers/meetup.py`
- Modify: `tests/unit/test_settings.py`

- [ ] **Step 1: Write failing tests for renamed field and new subclass**

Add to `tests/unit/test_settings.py` (inside `class TestLoadSettings`):

```python
def test_meetups_thread_id_loaded_from_config(self, tmp_path):
    """meetups_thread_id is read from config."""
    config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
meetups_thread_id = "42"

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    settings = load_settings(config_file)
    assert settings.telegram.regulars.meetups_thread_id == "42"

def test_stats_thread_id_loaded_from_config(self, tmp_path):
    """stats_thread_id is read from config for regulars."""
    config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
stats_thread_id = "99"

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    settings = load_settings(config_file)
    assert settings.telegram.regulars.stats_thread_id == "99"

def test_stats_thread_id_defaults_to_empty(self, tmp_path):
    """stats_thread_id is empty string when not configured."""
    config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    settings = load_settings(config_file)
    assert settings.telegram.regulars.stats_thread_id == ""
    assert settings.telegram.regulars.has_stats_thread() is False

def test_has_stats_thread_true_when_set(self, tmp_path):
    """has_stats_thread() returns True when stats_thread_id is set."""
    config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
stats_thread_id = "55"

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    settings = load_settings(config_file)
    assert settings.telegram.regulars.has_stats_thread() is True
```

Also add to the `TestTelegramSettings` class:

```python
def test_substitutes_has_no_stats_thread_id(self):
    """Substitutes settings do not have a stats_thread_id attribute."""
    from pyball.settings import TelegramChatSettings
    subs = TelegramChatSettings(chat_id=123, meetups_thread_id="")
    assert not hasattr(subs, "stats_thread_id")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run nox -e test -- tests/unit/test_settings.py -v
```

Expected: multiple failures (`AttributeError: meetups_thread_id`, `AttributeError: stats_thread_id`)

- [ ] **Step 3: Update `pyball/settings.py`**

Replace the `TelegramChatSettings` dataclass and update `TelegramSettings` and `load_settings`:

```python
@dataclass
class TelegramChatSettings:
    """Telegram chat configuration for regulars or substitutes."""

    chat_id: int = 0
    meetups_thread_id: str | int = ""

    def has_meetups_thread(self) -> bool:
        """Check if a meetups thread ID is configured."""
        return bool(self.meetups_thread_id)


@dataclass
class RegularsChatSettings(TelegramChatSettings):
    """Telegram chat configuration for the regulars group."""

    stats_thread_id: str | int = ""

    def has_stats_thread(self) -> bool:
        """Check if a stats thread ID is configured."""
        return bool(self.stats_thread_id)
```

Update `TelegramSettings` to use `RegularsChatSettings`:

```python
@dataclass
class TelegramSettings:
    """Telegram bot and chat configuration."""

    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: RegularsChatSettings = field(default_factory=RegularsChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids
```

Update `load_settings` — replace the `regulars` and `substitutes` construction blocks:

```python
    regulars = RegularsChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override("telegram_regulars", "chat_id", regulars_cfg.get("chat_id", 0))
        ),
        meetups_thread_id=_get_env_override(
            "telegram_regulars",
            "meetups_thread_id",
            regulars_cfg.get("meetups_thread_id", ""),
        ),
        stats_thread_id=_get_env_override(
            "telegram_regulars",
            "stats_thread_id",
            regulars_cfg.get("stats_thread_id", ""),
        ),
    )
    substitutes = TelegramChatSettings(
        chat_id=_parse_chat_id(
            _get_env_override(
                "telegram_substitutes", "chat_id", substitutes_cfg.get("chat_id", 0)
            )
        ),
        meetups_thread_id=_get_env_override(
            "telegram_substitutes",
            "meetups_thread_id",
            substitutes_cfg.get("meetups_thread_id", ""),
        ),
    )
```

Add `RegularsChatSettings` to the import list at the top of `tests/unit/test_settings.py`:

```python
from pyball.settings import (
    LocaleSettings,
    RegularsChatSettings,
    SettingsValidationError,
    TelegramSettings,
    load_settings,
)
```

- [ ] **Step 4: Update `example.config.toml`**

Replace the `[telegram.regulars]` section:

```toml
[telegram.regulars]
# Required: The main chat ID (negative number for groups)
# Override with PYBALL_TELEGRAM_REGULARS_CHAT_ID
chat_id = -1001234567890

# Optional: The forum topic thread for meetup callup messages
# Override with PYBALL_TELEGRAM_REGULARS_MEETUPS_THREAD_ID
meetups_thread_id = ""

# Optional: The forum topic thread where post-match statistics are posted
# Override with PYBALL_TELEGRAM_REGULARS_STATS_THREAD_ID
stats_thread_id = ""
```

Replace the `[telegram.substitutes]` section (add comment for meetups_thread_id):

```toml
[telegram.substitutes]
# Required: The substitutes chat ID (negative number for groups)
# Override with PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID
chat_id = -1001234567891

# Optional: The forum topic thread for meetup callup messages
# Override with PYBALL_TELEGRAM_SUBSTITUTES_MEETUPS_THREAD_ID
meetups_thread_id = ""
```

- [ ] **Step 5: Update `pyball/bot/handlers/meetup.py` — three occurrences**

Change line 215 (inside `_send_callup_messages`):
```python
# Before:
message_thread_id=settings.telegram.regulars.thread_id or None,
# After:
message_thread_id=settings.telegram.regulars.meetups_thread_id or None,
```

Change line 225 (the `MessageTracking` construction for regulars):
```python
# Before:
thread_id=settings.telegram.regulars.thread_id or None,
# After:
thread_id=settings.telegram.regulars.meetups_thread_id or None,
```

Change line 516 (substitutes local variable):
```python
# Before:
thread_id = settings.telegram.substitutes.thread_id
# After:
thread_id = settings.telegram.substitutes.meetups_thread_id
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
poetry run nox -e test -- tests/unit/test_settings.py -v
```

Expected: all tests PASS

- [ ] **Step 7: Run full lint to confirm 10.00/10**

```bash
poetry run nox -e lint
```

Expected: all checks pass, pylint 10.00/10

- [ ] **Step 8: Commit**

```bash
git add pyball/settings.py example.config.toml pyball/bot/handlers/meetup.py tests/unit/test_settings.py
git commit -m "refactor(settings): rename thread_id to meetups_thread_id, add RegularsChatSettings with stats_thread_id"
```

---

### Task 2: `ComputeStats` use case

**Files:**
- Create: `pyball/application/meetup/compute_stats.py`
- Modify: `pyball/application/meetup/__init__.py`
- Create: `tests/unit/application/test_compute_stats.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/application/test_compute_stats.py`:

```python
"""Tests for ComputeStats use case."""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    ComputeStats,
    PlayerStats,
    StatsScopedReport,
    StatsReport,
)
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, PlayerId, Team
from pyball.domain.player.models import Player


def make_player(name: str) -> Player:
    """Create a player with a generated ID."""
    return Player.create(name=name, group="regular")


def make_meetup(
    date_: datetime,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
    events: list[GoalEvent] | None = None,
) -> Meetup:
    """Create a finished meetup with teams and result."""
    meetup = Meetup.create(date=date_, location="Test Park")
    for pid in team_a + team_b:
        meetup.add_player(pid)
    meetup.teams = [Team.create("A", team_a), Team.create("B", team_b)]
    meetup.set_result(
        MatchResult(score_a=score_a, score_b=score_b, events=tuple(events or []))
    )
    return meetup


def make_repos(meetups, players):
    """Return (meetup_repo, player_repo) fakes."""
    meetup_repo = MagicMock()
    meetup_repo.find_all.return_value = meetups
    player_repo = MagicMock()
    player_repo.find_all.return_value = players
    return meetup_repo, player_repo


class TestComputeStatsEmpty:
    """Edge cases: empty or unfinished meetups."""

    def test_no_meetups_returns_empty_scopes(self):
        """No meetups → empty player and chemistry lists in both scopes."""
        meetup_repo, player_repo = make_repos([], [])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert isinstance(report, StatsReport)
        assert report.all_time.players == []
        assert report.season.players == []
        assert report.all_time.chemistry == []

    def test_meetup_without_result_is_excluded(self):
        """Meetups with no result set are ignored."""
        player = make_player("Alice")
        meetup = Meetup.create(date=datetime(2026, 1, 10, 20, 0), location="Park")
        meetup.add_player(player.id)
        meetup_repo, player_repo = make_repos([meetup], [player])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert report.all_time.players == []


class TestComputeStatsGoalsAndAssists:
    """Goal and assist counting."""

    def test_goal_increments_scorer(self):
        """A goal event increments the scorer's goal count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id], [bob.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals == 1

    def test_assist_increments_assistant(self):
        """A goal event with an assistant increments the assistant's assist count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=bob.id,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id, bob.id], [charlie.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert bob_stats.assists == 1

    def test_no_assist_does_not_crash(self):
        """A goal event with no assistant is handled cleanly."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id, assistant_id=None, team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals == 1
        assert alice_stats.assists == 0


class TestComputeStatsWinDrawLoss:
    """Win, draw, loss counting per player."""

    def test_team_a_win(self):
        """Team A players get a win when score_a > score_b."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 2, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert alice_stats.wins == 1 and alice_stats.losses == 0
        assert bob_stats.losses == 1 and bob_stats.wins == 0

    def test_team_b_win(self):
        """Team B players get a win when score_b > score_a."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 3)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert bob_stats.wins == 1
        assert alice_stats.losses == 1

    def test_draw(self):
        """Both teams get a draw when scores are equal."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        for p in report.all_time.players:
            assert p.draws == 1 and p.wins == 0 and p.losses == 0

    def test_points_calculation(self):
        """Points = wins*3 + draws."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins one, draws one → 3 + 1 = 4 pts
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 2, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points == 4

    def test_players_sorted_by_points_desc(self):
        """Players list is sorted by points descending."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins, Bob loses
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert report.all_time.players[0].player_name == "Alice"


class TestComputeStatsSeasonFilter:
    """Season boundary filtering."""

    def test_meetup_in_season_is_included(self):
        """A meetup after season start (Sep 1 of current year) is in the season scope."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Season 2025/2026: starts 2025-09-01
        meetup = make_meetup(datetime(2025, 10, 5, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.season.players) > 0

    def test_meetup_before_season_excluded_from_season(self):
        """A meetup before season start is excluded from season scope but not all-time."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # 2024-05-01 is before the 2024/2025 season would start at 2024-09-01
        # On test date 2026-04-13, season starts 2025-09-01, so 2024-05-01 is excluded
        meetup = make_meetup(datetime(2024, 5, 1, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.season.players) == 0
        assert len(report.all_time.players) > 0


class TestComputeStatsChemistry:
    """Chemistry pair counting."""

    def test_chemistry_pair_counted(self):
        """A scorer+assistant pair increments the chemistry count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        event = GoalEvent(
            scorer_id=alice.id, assistant_id=bob.id, team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id, bob.id], [charlie.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.chemistry) == 1
        pair = report.all_time.chemistry[0]
        assert pair.scorer_name == "Alice"
        assert pair.assistant_name == "Bob"
        assert pair.count == 1

    def test_chemistry_no_pair_when_no_assistant(self):
        """A goal without an assistant does not create a chemistry pair."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id, assistant_id=None, team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert report.all_time.chemistry == []

    def test_chemistry_top_10_only(self):
        """Only the top 10 chemistry pairs by count are returned."""
        # Create 11 different scorer+assistant pairs
        players = [make_player(f"Player{i}") for i in range(22)]
        events = []
        meetups = []
        for i in range(11):
            scorer = players[i * 2]
            assistant = players[i * 2 + 1]
            # Pair i appears (i+1) times across (i+1) meetups
            for j in range(i + 1):
                event = GoalEvent(
                    scorer_id=scorer.id, assistant_id=assistant.id, team="A",
                    timestamp=datetime(2026, 1, 10, 20, 5),
                )
                m = make_meetup(
                    datetime(2026, 1, 10 + i * 7 + j, 20, 0),
                    [scorer.id, assistant.id], [players[0].id], 1, 0, [event]
                )
                meetups.append(m)
        meetup_repo, player_repo = make_repos(meetups, players)
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.chemistry) == 10


class TestComputeStatsRankDelta:
    """Rank delta computation (trend indicators)."""

    def test_rank_delta_none_when_only_one_meetup(self):
        """With only one finished meetup there is no previous ranking — all deltas are None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        for p in report.all_time.players:
            assert p.rank_delta is None

    def test_rank_delta_zero_when_position_unchanged(self):
        """A player who stays in the same position gets delta 0."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins both matches — stays 1st
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.rank_delta == 0

    def test_rank_delta_positive_when_moved_up(self):
        """A player who moved up in ranking gets a positive delta."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # meetup1: Bob wins (Bob 1st, Alice 2nd)
        # meetup2: Alice wins (Alice moves to 1st → delta = +1)
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 1)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.rank_delta == 1

    def test_rank_delta_negative_when_dropped(self):
        """A player who dropped in ranking gets a negative delta."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # meetup1: Alice wins (Alice 1st)
        # meetup2: Bob wins (Bob catches up — if Bob overtakes, Alice drops)
        # After meetup1: Alice 3pts, Bob 0pts
        # After meetup2: Alice 3pts, Bob 3pts — Bob joins Alice at top
        #   To make Alice clearly drop: give Bob 2 wins in meetup2 context
        # Simpler: 3 meetups — Alice wins first, Bob wins next two
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 0, 1)
        meetup3 = make_meetup(datetime(2026, 1, 24, 20, 0), [alice.id], [bob.id], 0, 1)
        meetup_repo, player_repo = make_repos([meetup1, meetup2, meetup3], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        # After all 3: Bob 6pts (1st), Alice 3pts (2nd)
        # Previous (without meetup3): Alice 3pts (1st), Bob 3pts (2nd tie or 2nd)
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.rank_delta is not None
        assert alice_stats.rank_delta < 0  # Alice dropped

    def test_rank_delta_none_for_new_player(self):
        """A player absent from the previous ranking gets rank_delta=None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        # meetup1: Alice vs Bob (no Charlie)
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        # meetup2: Alice vs Charlie (Charlie's first appearance)
        meetup2 = make_meetup(
            datetime(2026, 1, 17, 20, 0), [alice.id], [charlie.id], 1, 0
        )
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        charlie_stats = next(p for p in report.all_time.players if p.player_name == "Charlie")
        assert charlie_stats.rank_delta is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
poetry run nox -e test -- tests/unit/application/test_compute_stats.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyball.application.meetup.compute_stats'`

- [ ] **Step 3: Create `pyball/application/meetup/compute_stats.py`**

```python
"""Compute match statistics use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


@dataclass
class PlayerStats:
    """Aggregated statistics for a single player."""

    player_id: str
    player_name: str
    goals: int
    assists: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    rank_delta: int | None  # positive = moved up, negative = dropped, None = new entry

    @property
    def points(self) -> int:
        """Return league points: win=3, draw=1, loss=0."""
        return self.wins * 3 + self.draws


@dataclass
class ChemistryPair:
    """A scorer+assistant pair and how many times they combined."""

    scorer_name: str
    assistant_name: str
    count: int


@dataclass
class StatsScopedReport:
    """Statistics for a single time scope (season or all-time)."""

    players: list[PlayerStats]
    chemistry: list[ChemistryPair]


@dataclass
class StatsReport:
    """Full statistics report with season and all-time scopes."""

    season: StatsScopedReport
    all_time: StatsScopedReport


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    return date(today.year - 1, 9, 1)


def _aggregate(
    meetups: list,
    player_names: dict[str, str],
) -> tuple[dict[str, dict], dict[tuple[str, str], int]]:
    """Aggregate raw stats from a list of meetups.

    Returns:
        player_data: player_id → {"goals", "assists", "mp", "w", "d", "l"}
        chemistry_counts: (scorer_id, assistant_id) → count
    """
    player_data: dict[str, dict] = {}
    chemistry_counts: dict[tuple[str, str], int] = {}

    for meetup in meetups:
        if meetup.result is None or meetup.teams is None:
            continue

        score_a = meetup.result.score_a
        score_b = meetup.result.score_b

        for team in meetup.teams:
            team_wins = (team.name == "A" and score_a > score_b) or (
                team.name == "B" and score_b > score_a
            )
            team_draws = score_a == score_b

            for player_id in team.players:
                pid = str(player_id.value)
                if pid not in player_data:
                    player_data[pid] = {
                        "goals": 0,
                        "assists": 0,
                        "mp": 0,
                        "w": 0,
                        "d": 0,
                        "l": 0,
                    }
                player_data[pid]["mp"] += 1
                if team_wins:
                    player_data[pid]["w"] += 1
                elif team_draws:
                    player_data[pid]["d"] += 1
                else:
                    player_data[pid]["l"] += 1

        for event in meetup.result.events:
            scorer_id = str(event.scorer_id.value)
            if scorer_id not in player_data:
                player_data[scorer_id] = {
                    "goals": 0,
                    "assists": 0,
                    "mp": 0,
                    "w": 0,
                    "d": 0,
                    "l": 0,
                }
            player_data[scorer_id]["goals"] += 1

            if event.assistant_id is not None:
                assistant_id = str(event.assistant_id.value)
                if assistant_id not in player_data:
                    player_data[assistant_id] = {
                        "goals": 0,
                        "assists": 0,
                        "mp": 0,
                        "w": 0,
                        "d": 0,
                        "l": 0,
                    }
                player_data[assistant_id]["assists"] += 1
                pair = (scorer_id, assistant_id)
                chemistry_counts[pair] = chemistry_counts.get(pair, 0) + 1

    return player_data, chemistry_counts


def _build_scoped_report(
    meetups: list,
    player_names: dict[str, str],
    prev_meetups: list | None = None,
) -> StatsScopedReport:
    """Build a StatsScopedReport, computing rank_delta from prev_meetups if provided."""
    player_data, chemistry_counts = _aggregate(meetups, player_names)

    stats_list = [
        PlayerStats(
            player_id=pid,
            player_name=player_names.get(pid, pid),
            goals=d["goals"],
            assists=d["assists"],
            matches_played=d["mp"],
            wins=d["w"],
            draws=d["d"],
            losses=d["l"],
            rank_delta=None,
        )
        for pid, d in player_data.items()
    ]
    stats_list.sort(key=lambda p: p.points, reverse=True)

    if prev_meetups is not None:
        prev_data, _ = _aggregate(prev_meetups, player_names)
        prev_ranked = sorted(
            prev_data.keys(),
            key=lambda pid: prev_data[pid]["w"] * 3 + prev_data[pid]["d"],
            reverse=True,
        )
        prev_rank = {pid: i + 1 for i, pid in enumerate(prev_ranked)}
        for i, player in enumerate(stats_list):
            current_pos = i + 1
            if player.player_id in prev_rank:
                player.rank_delta = prev_rank[player.player_id] - current_pos

    chemistry = sorted(
        [
            ChemistryPair(
                scorer_name=player_names.get(scorer_id, scorer_id),
                assistant_name=player_names.get(assistant_id, assistant_id),
                count=cnt,
            )
            for (scorer_id, assistant_id), cnt in chemistry_counts.items()
        ],
        key=lambda c: c.count,
        reverse=True,
    )[:10]

    return StatsScopedReport(players=stats_list, chemistry=chemistry)


class ComputeStats:
    """Use case for computing post-match player statistics."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ) -> None:
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self) -> StatsReport:
        """Compute and return season and all-time statistics.

        Returns:
            StatsReport with season and all_time StatsScopedReports.
        """
        all_meetups = self.meetup_repository.find_all()
        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        today = date.today()
        season_start = _season_start(today)

        finished = [m for m in all_meetups if m.result is not None]
        season_meetups = [m for m in finished if m.date.date() >= season_start]

        if finished:
            latest = max(finished, key=lambda m: m.date)
            prev_all = [m for m in finished if m is not latest]
            prev_season = [m for m in season_meetups if m is not latest]
        else:
            prev_all = None
            prev_season = None

        return StatsReport(
            season=_build_scoped_report(season_meetups, player_names, prev_season),
            all_time=_build_scoped_report(finished, player_names, prev_all),
        )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
poetry run nox -e test -- tests/unit/application/test_compute_stats.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Export from `pyball/application/meetup/__init__.py`**

Add to the imports and `__all__`:

```python
from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    ComputeStats,
    PlayerStats,
    StatsScopedReport,
    StatsReport,
)
```

And add to `__all__`:

```python
    "ComputeStats",
    "StatsReport",
    "StatsScopedReport",
    "PlayerStats",
    "ChemistryPair",
```

- [ ] **Step 6: Run lint**

```bash
poetry run nox -e lint
```

Expected: pylint 10.00/10, all checks pass

- [ ] **Step 7: Commit**

```bash
git add pyball/application/meetup/compute_stats.py pyball/application/meetup/__init__.py tests/unit/application/test_compute_stats.py
git commit -m "feat(application): add ComputeStats use case with season/all-time scopes and rank deltas"
```

---

### Task 3: `StatsImageRenderer`

**Files:**
- Modify: `pyproject.toml`
- Create: `pyball/infrastructure/images/__init__.py`
- Create: `pyball/infrastructure/images/stats_renderer.py`
- Create: `tests/unit/infrastructure/test_stats_renderer.py`

- [ ] **Step 1: Add `matplotlib` to `pyproject.toml`**

In the `[tool.poetry.dependencies]` section, add:

```toml
matplotlib = ">=3.7"
```

Then install:

```bash
poetry install
```

Expected: matplotlib installed successfully

- [ ] **Step 2: Write failing tests**

Create `tests/unit/infrastructure/test_stats_renderer.py`:

```python
"""Smoke tests for StatsImageRenderer."""

import pytest

from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    PlayerStats,
    StatsScopedReport,
    StatsReport,
)
from pyball.infrastructure.images.stats_renderer import StatsImageRenderer


def make_empty_report() -> StatsReport:
    """Return a StatsReport with no players or chemistry."""
    empty = StatsScopedReport(players=[], chemistry=[])
    return StatsReport(season=empty, all_time=empty)


def make_full_report() -> StatsReport:
    """Return a StatsReport with 3 players and 2 chemistry pairs."""
    players = [
        PlayerStats(
            player_id=f"id-{i}",
            player_name=f"Player{i}",
            goals=5 - i,
            assists=i,
            matches_played=10,
            wins=5 - i,
            draws=1,
            losses=i,
            rank_delta=i - 1,  # mix of positive, zero, negative
        )
        for i in range(3)
    ]
    players[2].rank_delta = None  # new entry
    chemistry = [
        ChemistryPair(scorer_name="Player0", assistant_name="Player1", count=3),
        ChemistryPair(scorer_name="Player1", assistant_name="Player2", count=1),
    ]
    scoped = StatsScopedReport(players=players, chemistry=chemistry)
    return StatsReport(season=scoped, all_time=scoped)


class TestStatsImageRenderer:
    """Smoke tests for StatsImageRenderer.render()."""

    def test_render_returns_two_bytes_objects(self):
        """render() returns a tuple of two non-empty bytes objects."""
        report = make_full_report()
        season_png, alltime_png = StatsImageRenderer().render(report)
        assert isinstance(season_png, bytes) and len(season_png) > 0
        assert isinstance(alltime_png, bytes) and len(alltime_png) > 0

    def test_render_produces_valid_png(self):
        """render() output starts with the PNG magic bytes."""
        report = make_full_report()
        season_png, alltime_png = StatsImageRenderer().render(report)
        png_magic = b"\x89PNG"
        assert season_png[:4] == png_magic
        assert alltime_png[:4] == png_magic

    def test_render_empty_report_does_not_raise(self):
        """render() handles an empty report without raising."""
        report = make_empty_report()
        season_png, alltime_png = StatsImageRenderer().render(report)
        assert isinstance(season_png, bytes)
        assert isinstance(alltime_png, bytes)

    def test_season_and_alltime_images_differ(self):
        """season and all_time images are different bytes when data differs."""
        players_season = [
            PlayerStats(
                player_id="id-0", player_name="Alice", goals=3, assists=1,
                matches_played=5, wins=3, draws=0, losses=2, rank_delta=None,
            )
        ]
        players_all = [
            PlayerStats(
                player_id="id-0", player_name="Alice", goals=10, assists=5,
                matches_played=20, wins=12, draws=2, losses=6, rank_delta=0,
            )
        ]
        report = StatsReport(
            season=StatsScopedReport(players=players_season, chemistry=[]),
            all_time=StatsScopedReport(players=players_all, chemistry=[]),
        )
        season_png, alltime_png = StatsImageRenderer().render(report)
        assert season_png != alltime_png
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
poetry run nox -e test -- tests/unit/infrastructure/test_stats_renderer.py -v
```

Expected: `ModuleNotFoundError: No module named 'pyball.infrastructure.images'`

- [ ] **Step 4: Create package and renderer**

Create `pyball/infrastructure/images/__init__.py` (empty):

```python
"""Image generation infrastructure."""
```

Create `pyball/infrastructure/images/stats_renderer.py`:

```python
"""Statistics image renderer using matplotlib."""

from __future__ import annotations

import io

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from pyball.application.meetup.compute_stats import (
    PlayerStats,
    StatsScopedReport,
    StatsReport,
)

plt.switch_backend("agg")

_TREND_SYMBOLS = {None: "★ ", "up": "▲ ", "down": "▼ ", "same": "─ "}
_COLOR_GOALS = "#e74c3c"
_COLOR_ASSISTS = "#3498db"
_COLOR_CHEMISTRY = "#2ecc71"
_COLOR_TABLE_HEADER = "#2c3e50"
_COLOR_TABLE_ROW_ODD = "#ecf0f1"
_COLOR_TABLE_ROW_EVEN = "#ffffff"


def _trend_prefix(rank_delta: int | None) -> str:
    """Return a unicode trend symbol based on rank_delta."""
    if rank_delta is None:
        return _TREND_SYMBOLS[None]
    if rank_delta > 0:
        return _TREND_SYMBOLS["up"]
    if rank_delta < 0:
        return _TREND_SYMBOLS["down"]
    return _TREND_SYMBOLS["same"]


def _labeled_name(player: PlayerStats) -> str:
    """Return the player name prefixed with its trend symbol."""
    return f"{_trend_prefix(player.rank_delta)}{player.player_name}"


class StatsImageRenderer:
    """Renders a StatsReport into two PNG images (season and all-time)."""

    def render(self, report: StatsReport) -> tuple[bytes, bytes]:
        """Generate PNG images for season and all-time scopes.

        Args:
            report: Fully computed StatsReport.

        Returns:
            Tuple of (season_png, all_time_png) as raw bytes.
        """
        return (
            self._render_scope(report.season, "Esta temporada"),
            self._render_scope(report.all_time, "Histórico"),
        )

    def _render_scope(self, scoped: StatsScopedReport, title: str) -> bytes:
        """Render a single scope into a PNG bytes object."""
        top_players = scoped.players[:10]
        top_chemistry = scoped.chemistry[:10]

        fig, axes = plt.subplots(3, 1, figsize=(8, 14))
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)

        self._render_goals_assists(axes[0], top_players)
        self._render_points_table(axes[1], top_players)
        self._render_chemistry(axes[2], top_chemistry)

        plt.tight_layout(rect=[0, 0, 1, 0.97])

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def _render_goals_assists(self, ax, players: list[PlayerStats]) -> None:
        """Render the goals & assists horizontal grouped bar chart."""
        ax.set_title("Goles y asistencias", fontweight="bold")

        if not players:
            ax.axis("off")
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        sorted_players = sorted(players, key=lambda p: p.goals, reverse=True)
        names = [_labeled_name(p) for p in sorted_players]
        goals = [p.goals for p in sorted_players]
        assists = [p.assists for p in sorted_players]
        y = list(range(len(names)))

        ax.barh([i + 0.2 for i in y], goals, height=0.4, label="Goles", color=_COLOR_GOALS)
        ax.barh([i - 0.2 for i in y], assists, height=0.4, label="Asist.", color=_COLOR_ASSISTS)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.legend(fontsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    def _render_points_table(self, ax, players: list[PlayerStats]) -> None:
        """Render the points ranking as a matplotlib table."""
        ax.set_title("Clasificación", fontweight="bold")
        ax.axis("off")

        if not players:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        col_labels = ["Jugador", "PJ", "G", "E", "P", "Pts"]
        table_data = [
            [
                _labeled_name(p),
                str(p.matches_played),
                str(p.wins),
                str(p.draws),
                str(p.losses),
                str(p.points),
            ]
            for p in players
        ]

        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.4)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor(_COLOR_TABLE_HEADER)
                cell.set_text_props(color="white", fontweight="bold")
            else:
                cell.set_facecolor(
                    _COLOR_TABLE_ROW_ODD if row % 2 == 1 else _COLOR_TABLE_ROW_EVEN
                )
            if col == 0:
                cell.set_text_props(ha="left")

    def _render_chemistry(self, ax, chemistry) -> None:
        """Render the top chemistry duos as a horizontal bar chart."""
        ax.set_title("Parejas más frecuentes", fontweight="bold")

        if not chemistry:
            ax.axis("off")
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", transform=ax.transAxes)
            return

        labels = [f"{c.scorer_name} + {c.assistant_name}" for c in chemistry]
        counts = [c.count for c in chemistry]

        ax.barh(labels, counts, color=_COLOR_CHEMISTRY)
        ax.invert_yaxis()
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_yticklabels(labels, fontsize=9)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
poetry run nox -e test -- tests/unit/infrastructure/test_stats_renderer.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 6: Run lint**

```bash
poetry run nox -e lint
```

Expected: pylint 10.00/10, all checks pass. If mypy complains about matplotlib stubs, add to `pyproject.toml` under `[[tool.mypy.overrides]]`:

```toml
[[tool.mypy.overrides]]
ignore_missing_imports = true
module = ["decouple", "event_bus", "matplotlib", "matplotlib.*"]
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml pyball/infrastructure/images/ tests/unit/infrastructure/test_stats_renderer.py
git commit -m "feat(infrastructure): add StatsImageRenderer — matplotlib PNG generation for stats"
```

---

### Task 4: Wire stats posting into `app.py`

**Files:**
- Modify: `pyball/infrastructure/http/app.py`

- [ ] **Step 1: Add imports, `_post_match_stats` helper, wire into endpoint**

Open `pyball/infrastructure/http/app.py`. Add `asyncio` to the stdlib imports at the top and the two new application/infrastructure imports alongside the existing ones:

```python
import asyncio
import logging
```

```python
from pyball.application.meetup.compute_stats import ComputeStats
from pyball.application.meetup.finish_match import MeetupAlreadyClosedError
from pyball.bot.handlers.meetup import close_match_messages
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.infrastructure.images.stats_renderer import StatsImageRenderer
from pyball.infrastructure.telegram import TelegramMessageStore
```

Add a module-level async function after the existing imports and before `create_app`:

```python
async def _post_match_stats(
    bot: "telegram.Bot",
    container: "Container",
    settings: "Settings",
) -> None:
    """Compute and post statistics images to the regulars stats topic.

    Runs as a background asyncio task. Errors are logged and swallowed so
    they never affect the match-finish response.

    Args:
        bot: Telegram Bot instance for sending photos.
        container: DI container with repositories.
        settings: Application settings for chat/thread IDs.
    """
    try:
        report = ComputeStats(
            container.meetup_repository, container.player_repository
        ).execute()
        season_png, alltime_png = StatsImageRenderer().render(report)

        stats_thread_id = settings.telegram.regulars.stats_thread_id or None
        chat_id = settings.telegram.regulars.chat_id

        await bot.send_photo(
            chat_id=chat_id,
            photo=season_png,
            caption="📊 Esta temporada",
            message_thread_id=int(stats_thread_id) if stats_thread_id else None,
        )
        await bot.send_photo(
            chat_id=chat_id,
            photo=alltime_png,
            caption="📊 Histórico",
            message_thread_id=int(stats_thread_id) if stats_thread_id else None,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error posting match stats")
```

Inside the `finish_match` endpoint in `create_app`, after the `await close_match_messages(...)` line, add:

```python
        asyncio.create_task(_post_match_stats(bot, container, settings))
```

The full updated endpoint should look like:

```python
    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and update Telegram callup messages."""
        use_case = container.finish_match()
        events = [e.model_dump() for e in body.events]
        try:
            meetup = use_case.execute(
                body.meetup_date, events, {"A": body.finalScore.A, "B": body.finalScore.B}
            )
        except MeetupNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meetup not found") from exc
        except MeetupAlreadyClosedError as exc:
            raise HTTPException(status_code=409, detail="Match already closed") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        all_players = container.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}
        player_groups = {str(p.id.value): p.group for p in all_players}

        message_store = TelegramMessageStore(settings.paths.bot_messages_file)
        await close_match_messages(bot, message_store, meetup, player_names, player_groups)

        asyncio.create_task(_post_match_stats(bot, container, settings))

        return {
            "meetup_date": body.meetup_date,
            "score_a": meetup.result.score_a,
            "score_b": meetup.result.score_b,
        }
```

- [ ] **Step 2: Run full test suite**

```bash
poetry run nox -e test
```

Expected: all tests PASS

- [ ] **Step 3: Run lint**

```bash
poetry run nox -e lint
```

Expected: pylint 10.00/10, all checks pass

- [ ] **Step 4: Commit**

```bash
git add pyball/infrastructure/http/app.py
git commit -m "feat(http): post stats images to Telegram after match finish"
```
