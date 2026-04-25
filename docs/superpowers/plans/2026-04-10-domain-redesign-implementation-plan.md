# Domain & Bot Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign Player and Meetup domain models, application layer, and Telegram bot to add group to Player, simplify Meetup to single player list, and identify by date/fuzzy name instead of UUIDs.

**Architecture:** Add `group` field to Player (regular/substitute). Replace Meetup's dual lists (regulars/substitutes) with single `players` list. Enforce unique meetup dates. Add fuzzy name matching for player identification in commands. Display masked names in substitutes chat.

**Tech Stack:** Python 3.11+, python-telegram-bot 22.x, Pydantic 2.x, pytest

---

## File Structure

**Domain (modify):**
- `pyball/domain/player/models.py` - add group field
- `pyball/domain/meetup/models.py` - single players list, unique date validation
- `pyball/domain/player/errors.py` - add new errors
- `pyball/domain/meetup/errors.py` - add duplicate date error

**Application (modify + new):**
- `pyball/application/player/create_player.py` - add group parameter
- `pyball/application/player/change_group.py` - NEW: change player group
- `pyball/application/meetup/create_meetup.py` - unique date + location from settings
- `pyball/application/meetup/add_player.py` - single list version
- `pyball/application/container.py` - register new use cases
- `pyball/application/__init__.py` - export new use cases
- `pyball/application/fuzzy_match.py` - NEW: fuzzy name matching utility

**Bot (modify):**
- `pyball/bot/handlers/meetup.py` - use date + fuzzy name
- `pyball/bot/handlers/player.py` - add /change_group command
- `pyball/bot/formatters.py` - masked display for substitutes chat
- `pyball/bot/callbacks.py` - single list handler

**Tests (modify):**
- `tests/unit/domain/test_player.py` - update for group
- `tests/unit/domain/test_meetup.py` - update for single list
- `tests/unit/application/test_create_player.py` - update for group
- `tests/unit/application/test_meetup_use_cases.py` - update for single list
- `tests/unit/application/test_change_player_group.py` - NEW
- `tests/unit/bot/test_formatters.py` - update for masked display

---

## Task 1: Player Domain - Add Group Field

**Files:**
- Modify: `pyball/domain/player/models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/test_player.py
import pytest
from pyball.domain.player.models import Player, PlayerId

def test_create_player_with_group():
    player = Player.create(name="Mario", group="regular")
    assert player.name == "Mario"
    assert player.group == "regular"

def test_create_player_with_substitute_group():
    player = Player.create(name="Luigi", group="substitute")
    assert player.group == "substitute"

def test_create_player_invalid_group():
    with pytest.raises(ValueError):
        Player.create(name="Mario", group="invalid")

def test_set_group():
    player = Player.create(name="Mario", group="regular")
    player.set_group("substitute")
    assert player.group == "substitute"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_player.py -v`
Expected: FAIL - AttributeError: 'Player' has no attribute 'group'

- [ ] **Step 3: Implement in models.py**

```python
# pyball/domain/player/models.py - add group to Player class

@dataclass
class Player(Entity):
    """Player entity."""

    id: PlayerId
    name: str
    group: str

    def __post_init__(self):
        if not self.name:
            raise ValueError("Player name cannot be empty")
        if self.group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")

    @classmethod
    def create(cls, name: str, group: str) -> "Player":
        if not name or not name.strip():
            raise ValueError("Player name cannot be empty")
        if group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        return cls(id=PlayerId.generate(), name=name.strip(), group=group)

    def set_group(self, new_group: str) -> None:
        if new_group not in ("regular", "substitute"):
            raise ValueError("Player group must be 'regular' or 'substitute'")
        object.__setattr__(self, "group", new_group)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_player.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/domain/player/models.py tests/unit/domain/test_player.py
git commit -m "feat: add group field to Player domain"
```

---

## Task 2: Meetup Domain - Single Player List + Unique Date

**Files:**
- Modify: `pyball/domain/meetup/models.py`
- Modify: `pyball/domain/meetup/errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/test_meetup.py
import pytest
from datetime import datetime
from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.player.models import PlayerId

def test_create_meetup_with_location():
    meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
    assert meetup.location == "Parque Central"
    assert meetup.players == []

def test_meetup_add_player():
    meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
    player_id = PlayerId.generate()
    meetup.add_player(player_id)
    assert player_id in meetup.players

def test_meetup_remove_player():
    meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
    player_id = PlayerId.generate()
    meetup.add_player(player_id)
    meetup.remove_player(player_id)
    assert player_id not in meetup.players

def test_meetup_location_required():
    with pytest.raises(ValueError):
        Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_meetup.py -v`
Expected: FAIL - 'Meetup' has no attribute 'location', 'players'

- [ ] **Step 3: Implement in models.py**

```python
# pyball/domain/meetup/models.py

@dataclass
class Meetup(Entity):
    """Meetup entity - represents a football session."""

    id: MeetupId
    date: datetime
    location: str
    players: list[PlayerId] = field(default_factory=list)
    teams: list[Team] | None = None

    @classmethod
    def create(cls, date: datetime, location: str) -> "Meetup":
        if not location or not location.strip():
            raise ValueError("Location cannot be empty")
        return cls(id=MeetupId.generate(), date=date, location=location.strip())

    def add_player(self, player_id: PlayerId) -> None:
        if player_id not in self.players:
            self.players.append(player_id)

    def remove_player(self, player_id: PlayerId) -> None:
        if player_id not in self.players:
            raise PlayerNotInMeetupError(str(player_id.value))
        self.players.remove(player_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_meetup.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/domain/meetup/models.py pyball/domain/meetup/errors.py tests/unit/domain/test_meetup.py
git commit -m "feat: simplify Meetup to single player list"
```

---

## Task 3: Fuzzy Name Matching Utility

**Files:**
- Create: `pyball/application/fuzzy_match.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/application/test_fuzzy_match.py
import pytest
from pyball.application.fuzzy_match import fuzzy_match_player

class MockPlayer:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def test_fuzzy_match_exact():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mario", players)
    assert result.name == "Mario"

def test_fuzzy_match_partial():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mar", players)
    assert result.name == "Mario"

def test_fuzzy_match_no_match():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    with pytest.raises(ValueError, match="Player not found"):
        fuzzy_match_player("Pippo", players)

def test_fuzzy_match_ambiguous():
    players = [MockPlayer("1", "Marco"), MockPlayer("2", "Marcos")]
    with pytest.raises(ValueError, match="Multiple players match"):
        fuzzy_match_player("Mar", players)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_fuzzy_match.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Implement fuzzy_match.py**

```python
# pyball/application/fuzzy_match.py

import difflib
from dataclasses import dataclass


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy name matching."""
    player_id: str
    name: str


def fuzzy_match_player(query: str, players: list) -> FuzzyMatchResult:
    """Find player by fuzzy name match.
    
    Args:
        query: Search query (partial or full name)
        players: List of objects with 'id' and 'name' attributes
        
    Returns:
        FuzzyMatchResult with matched player
        
    Raises:
        ValueError: If no match or multiple ambiguous matches
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    query = query.strip().lower()
    names = [(p.id, p.name, p.name.lower()) for p in players]
    
    matches = [(pid, name) for pid, name, lower_name in names if lower_name == query]
    
    if not matches:
        close = difflib.get_close_matches(query, [n[2] for n in names], n=3, cutoff=0.6)
        matches = [(pid, name) for pid, name, lower_name in names if lower_name in close]
    
    if not matches:
        raise ValueError(f"Player not found: {query}")
    
    if len(matches) > 1:
        names_str = ", ".join(m[1] for m in matches)
        raise ValueError(f"Multiple players match '{query}': {names_str}")
    
    return FuzzyMatchResult(player_id=matches[0][0], name=matches[0][1])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_fuzzy_match.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/fuzzy_match.py tests/unit/application/test_fuzzy_match.py
git commit -m "feat: add fuzzy name matching utility"
```

---

## Task 4: CreatePlayer Use Case - Add Group

**Files:**
- Modify: `pyball/application/player/create_player.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/application/test_create_player.py
import pytest
from unittest.mock import MagicMock
from pyball.application.player.create_player import CreatePlayer

def test_create_player_with_group():
    repo = MagicMock()
    use_case = CreatePlayer(repo)
    
    player = use_case.execute(name="Mario", group="regular")
    
    assert player.name == "Mario"
    assert player.group == "regular"
    repo.save.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_create_player.py -v`
Expected: FAIL - missing group parameter

- [ ] **Step 3: Implement**

```python
# pyball/application/player/create_player.py
# Update __init__ and execute to require group parameter

class CreatePlayer:
    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, name: str, group: str) -> Player:
        existing = self.player_repository.find_all()
        if any(p.name.lower() == name.lower() for p in existing):
            raise PlayerAlreadyExistsError(name)
        
        player = Player.create(name=name, group=group)
        self.player_repository.save(player)
        return player
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_create_player.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/player/create_player.py tests/unit/application/test_create_player.py
git commit -m "feat: add group parameter to CreatePlayer use case"
```

---

## Task 5: ChangePlayerGroup Use Case

**Files:**
- Create: `pyball/application/player/change_group.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/application/test_change_player_group.py
import pytest
from unittest.mock import MagicMock
from pyball.application.player.change_group import ChangePlayerGroup
from pyball.domain.player.models import Player, PlayerId

def test_change_player_group():
    player = Player.create(name="Mario", group="regular")
    repo = MagicMock()
    repo.find_by_id.return_value = player
    
    use_case = ChangePlayerGroup(repo)
    result = use_case.execute(str(player.id.value), "substitute")
    
    assert result.group == "substitute"
    repo.save.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_change_player_group.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Implement**

```python
# pyball/application/player/change_group.py

from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository
from pyball.domain.player.errors import PlayerNotFoundError


class ChangePlayerGroup:
    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player_id: str, new_group: str) -> Player:
        if new_group not in ("regular", "substitute"):
            raise ValueError("Group must be 'regular' or 'substitute'")
        
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            raise PlayerNotFoundError(player_id)
        
        player.set_group(new_group)
        self.player_repository.save(player)
        return player
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_change_player_group.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/player/change_group.py tests/unit/application/test_change_player_group.py
git commit -m "feat: add ChangePlayerGroup use case"
```

---

## Task 6: CreateMeetup Use Case - Unique Date + Location

**Files:**
- Modify: `pyball/application/meetup/create_meetup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/application/test_meetup_use_cases.py
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from pyball.application.meetup.create_meetup import CreateMeetup

def test_create_meetup_with_location():
    repo = MagicMock()
    repo.find_all.return_value = []
    use_case = CreateMeetup(repo)
    
    meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0))
    
    assert meetup.location == "Parque Central"
    assert meetup.players == []

def test_create_meetup_duplicate_date():
    existing = [MagicMock(date=datetime(2024, 3, 20, 20, 0))]
    repo = MagicMock()
    repo.find_all.return_value = existing
    use_case = CreateMeetup(repo)
    
    with pytest.raises(ValueError, match="Meetup already exists"):
        use_case.execute(date=datetime(2024, 3, 20, 20, 0))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_meetup_use_cases.py -v`
Expected: FAIL - location parameter missing

- [ ] **Step 3: Implement**

```python
# pyball/application/meetup/create_meetup.py

from datetime import datetime

from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.meetup.repository import MeetupRepository


class DuplicateMeetupError(ValueError):
    pass


class CreateMeetup:
    def __init__(self, meetup_repository: MeetupRepository, default_location: str = "Parque Central"):
        self.meetup_repository = meetup_repository
        self.default_location = default_location

    def execute(self, date: datetime, location: str | None = None) -> Meetup:
        existing = self.meetup_repository.find_all()
        for meetup in existing:
            if meetup.date == date:
                raise DuplicateMeetupError("Meetup already exists at this time")
        
        meetup = Meetup.create(date=date, location=location or self.default_location)
        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_meetup_use_cases.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/create_meetup.py tests/unit/application/test_meetup_use_cases.py
git commit -m "feat: add unique date and location to CreateMeetup"
```

---

## Task 7: AddPlayerToMeetup Use Case - Single List + Fuzzy

**Files:**
- Modify: `pyball/application/meetup/add_player.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/application/test_meetup_use_cases.py - add test
def test_add_player_to_meetup_fuzzy():
    player_repo = MagicMock()
    player = Player.create(name="Mario", group="regular")
    player_repo.find_all.return_value = [player]
    
    meetup_repo = MagicMock()
    meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
    meetup_repo.find_all.return_value = [meetup]
    
    use_case = AddPlayerToMeetup(meetup_repo, player_repo)
    use_case.execute("2024-03-20 20:00", "Mario")
    
    assert player.id in meetup.players
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_meetup_use_cases.py -v`
Expected: FAIL - module not found or wrong signature

- [ ] **Step 3: Implement**

```python
# pyball/application/meetup/add_player.py
# Update to use date string + fuzzy name matching

from datetime import datetime
from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class AddPlayerToMeetup:
    def __init__(self, meetup_repository: MeetupRepository, player_repository: PlayerRepository):
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self, date_str: str, player_name: str) -> Meetup:
        try:
            meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Invalid date format. Use: YYYY-MM-DD HH:MM")
        
        all_meetups = self.meetup_repository.find_all()
        meetup = None
        for m in all_meetups:
            if m.date == meetup_date:
                meetup = m
                break
        
        if not meetup:
            raise ValueError(f"Meetup not found at {date_str}")
        
        all_players = self.player_repository.find_all()
        match = fuzzy_match_player(player_name, all_players)
        player_id = PlayerId.from_string(match.player_id)
        
        meetup.add_player(player_id)
        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_meetup_use_cases.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/application/meetup/add_player.py tests/unit/application/test_meetup_use_cases.py
git commit -m "feat: update AddPlayerToMeetup for date + fuzzy name"
```

---

## Task 8: Container + Application Exports

**Files:**
- Modify: `pyball/application/container.py`
- Modify: `pyball/application/__init__.py`

- [ ] **Step 1: Update container.py**

```python
# pyball/application/container.py - add imports and register new use cases
from pyball.application.player.create_player import CreatePlayer
from pyball.application.player.change_group import ChangePlayerGroup
# ...existing imports...

def create_meetup(self) -> CreateMeetup:
    return CreateMeetup(self.meetup_repository, self.settings.pyball.location)

def add_player_to_meetup(self) -> AddPlayerToMeetup:
    return AddPlayerToMeetup(self.meetup_repository, self.player_repository)

def change_player_group(self) -> ChangePlayerGroup:
    return ChangePlayerGroup(self.player_repository)
```

- [ ] **Step 2: Update __init__.py**

```python
# pyball/application/__init__.py - export new use cases
from pyball.application.player.create_player import CreatePlayer
from pyball.application.player.change_group import ChangePlayerGroup
# ...existing exports...

__all__ = [
    "CreatePlayer",
    "ChangePlayerGroup",
    # ...existing...
]
```

- [ ] **Step 3: Commit**

```bash
git add pyball/application/container.py pyball/application/__init__.py
git commit -m "feat: register new use cases in container"
```

---

## Task 9: Formatters - Masked Display

**Files:**
- Modify: `pyball/bot/formatters.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/bot/test_formatters.py
def test_format_main_message_all_unmasked():
    meetup = MagicMock()
    meetup.players = [player_regular.id, player_substitute.id]
    player_names = {player_regular.id: "Mario", player_substitute.id: "Luigi"}
    
    text = format_main_message(meetup, player_names)
    
    assert "Mario" in text
    assert "Luigi" in text

def test_format_subs_message_masked_regulars():
    meetup = MagicMock()
    meetup.players = [player_regular.id, player_substitute.id]
    meetup.date = datetime(2024, 3, 20, 20, 0)
    player_names = {player_regular.id: "Mario", player_substitute.id: "Luigi"}
    player_groups = {player_regular.id: "regular", player_substitute.id: "substitute"}
    
    text = format_subs_message(meetup, player_names, player_groups)
    
    assert "---------" in text  # masked regular
    assert "Luigi" in text  # unmasked substitute
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/bot/test_formatters.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# pyball/bot/formatters.py - update functions

def format_main_message(meetup, player_names, player_groups=None):
    """Format main message - all names unmasked."""
    lines = [f"*{meetup.date.strftime('%Y-%m-%d %H:%M')}*"]
    if meetup.location:
        lines.append(f"📍 {meetup.location}")
    
    if meetup.players:
        lines.append("\n*Jugadores:*")
        for player_id in meetup.players:
            name = player_names.get(player_id, str(player_id.value))
            lines.append(f"  • {name}")
    else:
        lines.append("\nAún no hay jugadores.")
    
    return "\n".join(lines)


def format_subs_message(meetup, player_names, player_groups):
    """Format substitutes message - regulars masked."""
    lines = [f"*{meetup.date.strftime('%Y-%m-%d %H:%M')}*"]
    
    if meetup.players:
        lines.append("\n*Jugadores:*")
        for player_id in meetup.players:
            group = player_groups.get(player_id, "regular")
            if group == "regular":
                lines.append(f"  • ---------")
            else:
                name = player_names.get(player_id, str(player_id.value))
                lines.append(f"  • {name}")
    
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/bot/test_formatters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: add masked display for substitutes chat"
```

---

## Task 10: Meetup Handlers - Date + Fuzzy

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`

- [ ] **Step 1: Implement handler updates**

Changes needed:
- Parse date string `YYYY-MM-DD HH:MM` instead of meetup_id
- Use fuzzy name matching to find player for /add_player, /remove_player
- Update /create_teams to use date string
- Update /list_meetups to show dates only (no UUIDs)
- Update /show_meetup to use date string
- Update /callup to save location from settings
- Update /search to use date string

- [ ] **Step 2: Commit**

```bash
git add pyball/bot/handlers/meetup.py
git commit -m "feat: update meetup handlers for date + fuzzy name"
```

---

## Task 11: Player Handler - Add /change_group

**Files:**
- Modify: `pyball/bot/handlers/player.py`

- [ ] **Step 1: Add handler**

```python
@authorized
async def change_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /change_group command."""
    container: Container = context.bot_data.get("container")
    if not container:
        container = Container()

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /change_group <player_name> <regular|substitute>")
        return

    player_name = context.args[0]
    new_group = context.args[1]

    if new_group not in ("regular", "substitute"):
        await update.message.reply_text("Group must be 'regular' or 'substitute'")
        return

    player_repo = container.player_repository
    all_players = player_repo.find_all()
    
    try:
        match = fuzzy_match_player(player_name, all_players)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    try:
        use_case = container.change_player_group()
        player = use_case.execute(match.player_id, new_group)
        await update.message.reply_text(f"Player {player.name} changed to {new_group}!")
    except Exception as e:
        await update.message.reply_text("Error changing player group.")
```

- [ ] **Step 2: Register in setup_player_handlers**

```python
def setup_player_handlers(application):
    application.add_handler(CommandHandler("add_player", add_player_handler))
    application.add_handler(CommandHandler("rename_player", rename_player_handler))
    application.add_handler(CommandHandler("delete_player", delete_player_handler))
    application.add_handler(CommandHandler("change_group", change_group_handler))  # NEW
```

- [ ] **Step 3: Commit**

```bash
git add pyball/bot/handlers/player.py pyball/bot/handlers/__init__.py
git commit -m "feat: add /change_group command"
```

---

## Task 12: Callbacks - Single List Handler

**Files:**
- Modify: `pyball/bot/callbacks.py`

- [ ] **Step 1: Update handler**

Replace action types:
- `join` → adds user to meetup.players
- `leave` → removes user from meetup.players

Removed: `join_sub`, `leave_sub`, `join`, `leave` separate logic.

- [ ] **Step 2: Commit**

```bash
git add pyball/bot/callbacks.py
git commit -m "feat: simplify callback handler for single player list"
```

---

## Task 13: Integration Test

**Files:**
- Modify: `tests/integration/test_json_repository.py`
- Create: `tests/integration/test_end_to_end.py` if needed

- [ ] **Step 1: Run existing tests**

Run: `poetry run nox -e test`
Expected: Pass after all changes

- [ ] **Step 2: Commit**

```bash
git add tests/
git commit -m "test: update integration tests"
```

---

## Execution Summary

**Plan complete.** All tasks defined with TDD approach. The order is:
1. Player domain (group field)
2. Meetup domain (single list)
3. Fuzzy matching utility
4. CreatePlayer use case
5. ChangePlayerGroup use case
6. CreateMeetup use case
7. AddPlayerToMeetup use case
8. Container/exports
9. Formatters
10. Meetup handlers
11. Player handler
12. Callbacks
13. Integration tests

Total: 13 tasks with ~65 steps.

**Which approach?**
1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints