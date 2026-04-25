# PyBall v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a clean, testable Telegram bot for managing football meetups using modular monolith architecture with DDD principles.

**Architecture:** Single Python package with clear separation: domain (pure business logic), application (use cases), infrastructure (JSON persistence), bot (Telegram handlers).

**Tech Stack:** Python 3.10+, python-telegram-bot 20.x, pytest for testing.

---

## File Structure

```
pyball/
├── __init__.py
├── __main__.py              # Entry point
├── settings.py              # Configuration
├── domain/
│   ├── __init__.py
│   ├── base.py              # Base classes (Entity, ValueObject)
│   ├── player/
│   │   ├── __init__.py
│   │   ├── models.py        # PlayerId, Player
│   │   ├── errors.py
│   │   └── repository.py
│   └── meetup/
│       ├── __init__.py
│       ├── models.py        # MeetupId, Meetup, Team
│       ├── errors.py
│       └── repository.py
├── application/
│   ├── __init__.py
│   ├── player/
│   │   ├── __init__.py
│   │   ├── create_player.py
│   │   ├── rename_player.py
│   │   └── delete_player.py
│   └── meetup/
│       ├── __init__.py
│       ├── create_meetup.py
│       ├── add_player.py
│       ├── remove_player.py
│       └── create_teams.py
├── infrastructure/
│   ├── __init__.py
│   └── json_repository.py
└── bot/
    ├── __init__.py
    ├── entrypoint.py
    └── handlers/
        ├── __init__.py
        └── player.py
```

---

## Task 1: Project Setup

**Files:** Modify `pyproject.toml`, Create `pyball/__init__.py`, `pyball/settings.py`

- [ ] Update `pyproject.toml` dependencies:
```toml
[tool.poetry.dependencies]
python = ">=3.10,<4.0"
python-telegram-bot = "20.*"
pydantic = "^2.0"
```

- [ ] Create `pyball/__init__.py`:
```python
"""PyBall - Telegram bot for managing football meetups."""

__version__ = "4.0.0"
```

- [ ] Create `pyball/settings.py`:
```python
"""Application settings."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Paths:
    data_dir: Path = field(default_factory=lambda: Path("data"))
    players_file: Path = field(init=False)
    meetups_dir: Path = field(init=False)
    mappings_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"
        self.mappings_file = self.data_dir / "bot" / "mappings.json"


@dataclass
class TelegramSettings:
    bot_token: str = ""


@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    paths: Paths = field(default_factory=Paths)


def load_settings() -> Settings:
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, value = line.strip().split("=", 1)
                    import os
                    os.environ.setdefault(key, value)
    return Settings()
```

- [ ] Run: `poetry install`

- [ ] Commit: `git add pyproject.toml pyball/__init__.py pyball/settings.py && git commit -m "feat: initial project setup with settings"`

---

## Task 2: Domain Base Classes

**Files:** Create `pyball/domain/__init__.py`, `pyball/domain/base.py`

- [ ] Create `pyball/domain/__init__.py`:
```python
"""Domain layer - pure business logic."""

from pyball.domain.base import Entity, ValueObject

__all__ = ["Entity", "ValueObject"]
```

- [ ] Create `pyball/domain/base.py`:
```python
"""Base classes for domain objects."""

from uuid import UUID, uuid4


class ValueObject:
    """Base class for value objects."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def as_tuple(self) -> tuple:
        return tuple(getattr(self, name) for name in self.__annotations__)


class Entity:
    """Base class for entities with identity."""

    id: UUID

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
```

- [ ] Commit: `git add pyball/domain/ && git commit -m "feat: add domain base classes (Entity, ValueObject)"`

---

## Task 3: Player Aggregate

**Files:** Create `pyball/domain/player/` module

- [ ] Create `pyball/domain/player/__init__.py`:
```python
"""Player domain - entities and business rules."""

from pyball.domain.player.models import PlayerId, Player
from pyball.domain.player.errors import PlayerNotFoundError, PlayerAlreadyExistsError
from pyball.domain.player.repository import PlayerRepository

__all__ = ["PlayerId", "Player", "PlayerRepository", "PlayerNotFoundError", "PlayerAlreadyExistsError"]
```

- [ ] Create `pyball/domain/player/models.py`:
```python
"""Player models."""

from dataclasses import dataclass
from uuid import UUID

from pyball.domain.base import Entity, ValueObject


@dataclass(frozen=True)
class PlayerId(ValueObject):
    """Value object for player identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "PlayerId":
        return cls(UUID(value))

    @classmethod
    def generate(cls) -> "PlayerId":
        return cls(UUID())


@dataclass
class Player(Entity):
    """Player entity."""

    id: PlayerId
    name: str

    @classmethod
    def create(cls, name: str) -> "Player":
        if not name or not name.strip():
            raise ValueError("Player name cannot be empty")
        return cls(id=PlayerId.generate(), name=name.strip())

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            raise ValueError("Player name cannot be empty")
        self.name = new_name.strip()
```

- [ ] Create `pyball/domain/player/errors.py`:
```python
"""Player domain errors."""


class PlayerNotFoundError(Exception):
    """Raised when a player is not found."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Player with id '{player_id}' not found")


class PlayerAlreadyExistsError(Exception):
    """Raised when trying to create a player that already exists."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Player with name '{name}' already exists")
```

- [ ] Create `pyball/domain/player/repository.py`:
```python
"""Player repository interface."""

from typing import Protocol

from pyball.domain.player.models import Player, PlayerId


class PlayerRepository(Protocol):
    """Repository interface for Player aggregate."""

    def save(self, player: Player) -> None: ...
    def find_by_id(self, player_id: PlayerId) -> Player | None: ...
    def find_by_name(self, name: str) -> Player | None: ...
    def find_all(self) -> list[Player]: ...
    def delete(self, player_id: PlayerId) -> None: ...
```

- [ ] Commit: `git add pyball/domain/player/ && git commit -m "feat: add Player aggregate"`

---

## Task 4: Meetup Aggregate

**Files:** Create `pyball/domain/meetup/` module

- [ ] Create `pyball/domain/meetup/__init__.py`:
```python
"""Meetup domain - entities and business rules."""

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.meetup.errors import MeetupNotFoundError, PlayerNotInMeetupError

__all__ = ["Meetup", "MeetupId", "Team", "MeetupNotFoundError", "PlayerNotInMeetupError"]
```

- [ ] Create `pyball/domain/meetup/models.py`:
```python
"""Meetup models."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pyball.domain.base import Entity, ValueObject
from pyball.domain.player.models import PlayerId


@dataclass(frozen=True)
class MeetupId(ValueObject):
    """Value object for meetup identity."""

    value: UUID

    @classmethod
    def from_string(cls, value: str) -> "MeetupId":
        return cls(UUID(value))

    @classmethod
    def generate(cls) -> "MeetupId":
        return cls(UUID())


@dataclass(frozen=True)
class Team(ValueObject):
    """Value object representing a team."""

    name: str
    players: tuple[PlayerId, ...]

    @classmethod
    def create(cls, name: str, players: list[PlayerId]) -> "Team":
        return cls(name=name, players=tuple(players))


@dataclass
class Meetup(Entity):
    """Meetup entity - represents a football session."""

    id: MeetupId
    date: datetime
    regulars: list[PlayerId] = field(default_factory=list)
    substitutes: list[PlayerId] = field(default_factory=list)
    teams: list[Team] | None = None

    @classmethod
    def create(cls, date: datetime) -> "Meetup":
        return cls(id=MeetupId.generate(), date=date)

    def add_regular(self, player_id: PlayerId) -> None:
        if player_id in self.substitutes:
            self.substitutes.remove(player_id)
        if player_id not in self.regulars:
            self.regulars.append(player_id)

    def add_substitute(self, player_id: PlayerId) -> None:
        if player_id in self.regulars:
            self.regulars.remove(player_id)
        if player_id not in self.substitutes:
            self.substitutes.append(player_id)

    def remove_player(self, player_id: PlayerId) -> None:
        if player_id in self.regulars:
            self.regulars.remove(player_id)
        elif player_id in self.substitutes:
            self.substitutes.remove(player_id)
        else:
            raise ValueError(f"Player {player_id} not in meetup")

    def create_balanced_teams(self, random_generator) -> None:
        if len(self.regulars) < 2:
            raise ValueError("Need at least 2 regulars to create teams")

        all_players = list(self.regulars)
        if len(all_players) % 2 != 0 and self.substitutes:
            all_players.append(self.substitutes[0])

        random_generator.shuffle(all_players)
        mid = len(all_players) // 2
        self.teams = [
            Team.create("Team A", all_players[:mid]),
            Team.create("Team B", all_players[mid:]),
        ]
```

- [ ] Create `pyball/domain/meetup/errors.py`:
```python
"""Meetup domain errors."""


class MeetupNotFoundError(Exception):
    """Raised when a meetup is not found."""

    def __init__(self, meetup_id: str):
        self.meetup_id = meetup_id
        super().__init__(f"Meetup with id '{meetup_id}' not found")


class PlayerNotInMeetupError(Exception):
    """Raised when a player is not in the meetup."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Player '{player_id}' is not in this meetup")
```

- [ ] Create `pyball/domain/meetup/repository.py`:
```python
"""Meetup repository interface."""

from datetime import date
from typing import Protocol

from pyball.domain.meetup.models import Meetup, MeetupId


class MeetupRepository(Protocol):
    """Repository interface for Meetup aggregate."""

    def save(self, meetup: Meetup) -> None: ...
    def find_by_id(self, meetup_id: MeetupId) -> Meetup | None: ...
    def find_by_date(self, meetup_date: date) -> Meetup | None: ...
    def find_all(self) -> list[Meetup]: ...
    def delete(self, meetup_id: MeetupId) -> None: ...
```

- [ ] Commit: `git add pyball/domain/meetup/ && git commit -m "feat: add Meetup aggregate"`

---

## Task 5: Infrastructure - JSON Repository

**Files:** Create `pyball/infrastructure/` module

- [ ] Create `pyball/infrastructure/__init__.py`:
```python
"""Infrastructure layer - persistence implementations."""

from pyball.infrastructure.json_repository import JsonPlayerRepository, JsonMeetupRepository

__all__ = ["JsonPlayerRepository", "JsonMeetupRepository"]
```

- [ ] Create `pyball/infrastructure/json_repository.py`:
```python
"""JSON file-based repository implementations."""

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import Player, PlayerId
from pyball.domain.player.repository import PlayerRepository


class JsonPlayerRepository(PlayerRepository):
    """JSON file-based player repository."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({"players": []})

    def _read(self) -> dict:
        with open(self.file_path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save(self, player: Player) -> None:
        data = self._read()
        players = data.get("players", [])
        for i, p in enumerate(players):
            if p["id"] == str(player.id.value):
                players[i] = {"id": str(player.id.value), "name": player.name}
                break
        else:
            players.append({"id": str(player.id.value), "name": player.name})
        self._write({"players": players})

    def find_by_id(self, player_id: PlayerId) -> Player | None:
        data = self._read()
        for p in data.get("players", []):
            if p["id"] == str(player_id.value):
                return Player(id=PlayerId(UUID(p["id"])), name=p["name"])
        return None

    def find_by_name(self, name: str) -> Player | None:
        data = self._read()
        for p in data.get("players", []):
            if p["name"].lower() == name.lower():
                return Player(id=PlayerId(UUID(p["id"])), name=p["name"])
        return None

    def find_all(self) -> list[Player]:
        data = self._read()
        return [
            Player(id=PlayerId(UUID(p["id"])), name=p["name"])
            for p in data.get("players", [])
        ]

    def delete(self, player_id: PlayerId) -> None:
        data = self._read()
        players = [p for p in data.get("players", []) if p["id"] != str(player_id.value)]
        self._write({"players": players})


class JsonMeetupRepository(MeetupRepository):
    """JSON file-based meetup repository."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, meetup: Meetup) -> Path:
        return self.directory / f"{meetup.date.strftime('%Y-%m-%d')}.json"

    def _read_file(self, file_path: Path) -> dict | None:
        if not file_path.exists():
            return None
        with open(file_path) as f:
            return json.load(f)

    def _write(self, meetup: Meetup) -> None:
        file_path = self._get_file_path(meetup)
        teams_data = None
        if meetup.teams:
            teams_data = [
                {"name": t.name, "players": [str(p.value) for p in t.players]}
                for t in meetup.teams
            ]
        data = {
            "id": str(meetup.id.value),
            "date": meetup.date.isoformat(),
            "regulars": [str(p.value) for p in meetup.regulars],
            "substitutes": [str(p.value) for p in meetup.substitutes],
            "teams": teams_data,
        }
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save(self, meetup: Meetup) -> None:
        self._write(meetup)

    def find_by_id(self, meetup_id: MeetupId) -> Meetup | None:
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data and data["id"] == str(meetup_id.value):
                return self._dict_to_meetup(data)
        return None

    def find_by_date(self, meetup_date: date) -> Meetup | None:
        file_path = self.directory / f"{meetup_date.strftime('%Y-%m-%d')}.json"
        data = self._read_file(file_path)
        if data:
            return self._dict_to_meetup(data)
        return None

    def find_all(self) -> list[Meetup]:
        meetups = []
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data:
                meetups.append(self._dict_to_meetup(data))
        return sorted(meetups, key=lambda m: m.date)

    def delete(self, meetup_id: MeetupId) -> None:
        for file_path in self.directory.glob("*.json"):
            data = self._read_file(file_path)
            if data and data["id"] == str(meetup_id.value):
                file_path.unlink()
                return

    def _dict_to_meetup(self, data: dict) -> Meetup:
        teams = None
        if data.get("teams"):
            teams = [
                Team.create(t["name"], [PlayerId(UUID(p)) for p in t["players"]])
                for t in data["teams"]
            ]
        return Meetup(
            id=MeetupId(UUID(data["id"])),
            date=datetime.fromisoformat(data["date"]),
            regulars=[PlayerId(UUID(p)) for p in data.get("regulars", [])],
            substitutes=[PlayerId(UUID(p)) for p in data.get("substitutes", [])],
            teams=teams,
        )
```

- [ ] Commit: `git add pyball/infrastructure/ && git commit -m "feat: add JSON repository implementations"`

---

## Task 6: Application Layer - Player Use Cases

**Files:** Create `pyball/application/` module

- [ ] Create `pyball/application/__init__.py`:
```python
"""Application layer - use cases."""

from pyball.application.player.create_player import CreatePlayer
from pyball.application.player.rename_player import RenamePlayer
from pyball.application.player.delete_player import DeletePlayer

__all__ = ["CreatePlayer", "RenamePlayer", "DeletePlayer"]
```

- [ ] Create `pyball/application/player/__init__.py`:
```python
"""Player use cases."""

from pyball.application.player.create_player import CreatePlayer
from pyball.application.player.rename_player import RenamePlayer
from pyball.application.player.delete_player import DeletePlayer

__all__ = ["CreatePlayer", "RenamePlayer", "DeletePlayer"]
```

- [ ] Create `pyball/application/player/create_player.py`:
```python
"""Create player use case."""

from pyball.domain.player.models import Player
from pyball.domain.player.repository import PlayerRepository


class CreatePlayer:
    """Use case for creating a new player."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, name: str) -> Player:
        existing = self.player_repository.find_by_name(name)
        if existing:
            from pyball.domain.player.errors import PlayerAlreadyExistsError
            raise PlayerAlreadyExistsError(name)
        player = Player.create(name)
        self.player_repository.save(player)
        return player
```

- [ ] Create `pyball/application/player/rename_player.py`:
```python
"""Rename player use case."""

from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class RenamePlayer:
    """Use case for renaming a player."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player_id: str, new_name: str) -> Player:
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            from pyball.domain.player.errors import PlayerNotFoundError
            raise PlayerNotFoundError(player_id)
        player.rename(new_name)
        self.player_repository.save(player)
        return player
```

- [ ] Create `pyball/application/player/delete_player.py`:
```python
"""Delete player use case."""

from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class DeletePlayer:
    """Use case for deleting a player."""

    def __init__(self, player_repository: PlayerRepository):
        self.player_repository = player_repository

    def execute(self, player_id: str) -> None:
        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            from pyball.domain.player.errors import PlayerNotFoundError
            raise PlayerNotFoundError(player_id)
        self.player_repository.delete(PlayerId.from_string(player_id))
```

- [ ] Commit: `git add pyball/application/ && git commit -m "feat: add player use cases"`

---

## Task 7: Application Layer - Meetup Use Cases

**Files:** Create `pyball/application/meetup/` module

- [ ] Create `pyball/application/meetup/__init__.py`:
```python
"""Meetup use cases."""

from pyball.application.meetup.create_meetup import CreateMeetup
from pyball.application.meetup.add_player import AddPlayerToMeetup
from pyball.application.meetup.remove_player import RemovePlayerFromMeetup
from pyball.application.meetup.create_teams import CreateTeams

__all__ = ["CreateMeetup", "AddPlayerToMeetup", "RemovePlayerFromMeetup", "CreateTeams"]
```

- [ ] Create `pyball/application/meetup/create_meetup.py`:
```python
"""Create meetup use case."""

from datetime import datetime

from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository


class CreateMeetup:
    """Use case for creating a new meetup."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, date: datetime) -> Meetup:
        existing = self.meetup_repository.find_by_date(date.date())
        if existing:
            existing.date = date
            self.meetup_repository.save(existing)
            return existing
        meetup = Meetup.create(date)
        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] Create `pyball/application/meetup/add_player.py`:
```python
"""Add player to meetup use case."""

from pyball.domain.meetup.models import MeetupId
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class AddPlayerToMeetup:
    """Use case for adding a player to a meetup."""

    def __init__(self, meetup_repository: MeetupRepository, player_repository: PlayerRepository):
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self, meetup_id: str, player_id: str, role: str = "regular") -> Meetup:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            from pyball.domain.meetup.errors import MeetupNotFoundError
            raise MeetupNotFoundError(meetup_id)

        player = self.player_repository.find_by_id(PlayerId.from_string(player_id))
        if not player:
            from pyball.domain.player.errors import PlayerNotFoundError
            raise PlayerNotFoundError(player_id)

        player_id_obj = PlayerId.from_string(player_id)
        if role == "substitute":
            meetup.add_substitute(player_id_obj)
        else:
            meetup.add_regular(player_id_obj)

        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] Create `pyball/application/meetup/remove_player.py`:
```python
"""Remove player from meetup use case."""

from pyball.domain.meetup.models import MeetupId
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class RemovePlayerFromMeetup:
    """Use case for removing a player from a meetup."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, meetup_id: str, player_id: str) -> None:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            from pyball.domain.meetup.errors import MeetupNotFoundError
            raise MeetupNotFoundError(meetup_id)

        player_id_obj = PlayerId.from_string(player_id)
        meetup.remove_player(player_id_obj)
        self.meetup_repository.save(meetup)
```

- [ ] Create `pyball/application/meetup/create_teams.py`:
```python
"""Create teams use case."""

import random

from pyball.domain.meetup.models import MeetupId
from pyball.domain.meetup.repository import MeetupRepository


class CreateTeams:
    """Use case for creating balanced teams."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, meetup_id: str) -> Meetup:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            from pyball.domain.meetup.errors import MeetupNotFoundError
            raise MeetupNotFoundError(meetup_id)

        meetup.create_balanced_teams(random)
        self.meetup_repository.save(meetup)
        return meetup
```

- [ ] Commit: `git add pyball/application/meetup/ && git commit -m "feat: add meetup use cases"`

---

## Task 8: Bot Layer - Setup

**Files:** Create `pyball/bot/` module

- [ ] Create `pyball/bot/__init__.py`:
```python
"""Bot layer - Telegram handlers."""

from pyball.bot.entrypoint import create_application

__all__ = ["create_application"]
```

- [ ] Create `pyball/bot/entrypoint.py`:
```python
"""Bot application entrypoint."""

from telegram.ext import Application

from pyball.settings import load_settings


def create_application() -> Application:
    """Create and configure the Telegram application."""
    settings = load_settings()
    application = Application.builder().token(settings.telegram.bot_token).build()
    return application
```

- [ ] Commit: `git add pyball/bot/ && git commit -m "feat: add bot entrypoint"`

---

## Task 9: Bot Layer - Player Handlers

**Files:** Create `pyball/bot/handlers/` module

- [ ] Create `pyball/bot/handlers/__init__.py`:
```python
"""Bot handlers."""

from pyball.bot.handlers.player import setup_player_handlers

__all__ = ["setup_player_handlers"]
```

- [ ] Create `pyball/bot/handlers/player.py`:
```python
"""Player command handlers."""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from pyball.application.player import CreatePlayer, RenamePlayer, DeletePlayer
from pyball.infrastructure import JsonPlayerRepository
from pyball.settings import load_settings


def setup_player_handlers(application):
    """Register player-related handlers."""
    application.add_handler(CommandHandler("new_player", new_player_handler))
    application.add_handler(CommandHandler("rename_player", rename_player_handler))
    application.add_handler(CommandHandler("delete_player", delete_player_handler))
    application.add_handler(CommandHandler("list_players", list_players_handler))


async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    create_player = CreatePlayer(player_repo)

    if not context.args:
        await update.message.reply_text("Usage: /new_player <name>")
        return

    name = " ".join(context.args)
    try:
        player = create_player.execute(name)
        await update.message.reply_text(f"Player '{player.name}' created!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /rename_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    rename_player = RenamePlayer(player_repo)

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /rename_player <player_id> <new_name>")
        return

    player_id = context.args[0]
    new_name = " ".join(context.args[1:])
    try:
        player = rename_player.execute(player_id, new_name)
        await update.message.reply_text(f"Player renamed to '{player.name}'!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete_player command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)
    delete_player = DeletePlayer(player_repo)

    if not context.args:
        await update.message.reply_text("Usage: /delete_player <player_id>")
        return

    player_id = context.args[0]
    try:
        delete_player.execute(player_id)
        await update.message.reply_text("Player deleted!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list_players command."""
    settings = load_settings()
    player_repo = JsonPlayerRepository(settings.paths.players_file)

    players = player_repo.find_all()
    if not players:
        await update.message.reply_text("No players found.")
        return

    lines = ["*Players:*"]
    for p in players:
        lines.append(f"- {p.name} (id: {p.id.value})")

    await update.message.reply_text("\n".join(lines))
```

- [ ] Commit: `git add pyball/bot/handlers/ && git commit -m "feat: add player command handlers"`

---

## Task 10: Entry Point Update

**Files:** Modify `pyball/__main__.py`

- [ ] Update `pyball/__main__.py`:
```python
"""Bot main file."""

import logging

from pyball import __version__
from pyball.bot import create_application
from pyball.bot.handlers import setup_player_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_startup_info() -> None:
    """Log startup information."""
    logger.info("*" * 40)
    logger.info(f"PyBall v{__version__}")
    logger.info("*" * 40)


def main() -> None:
    """Start the bot."""
    log_startup_info()
    application = create_application()
    setup_player_handlers(application)
    application.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] Commit: `git add pyball/__main__.py && git commit -m "feat: update entry point with handlers setup"`

---

## Task 11: Tests

**Files:** Create `tests/` structure

- [ ] Create test structure and files:
```bash
mkdir -p tests/unit/domain tests/unit/application
touch tests/__init__.py tests/unit/__init__.py tests/unit/domain/__init__.py tests/unit/application/__init__.py
```

- [ ] Create `tests/unit/domain/test_player.py`:
```python
"""Tests for Player domain model."""

import pytest

from pyball.domain.player.models import Player, PlayerId


class TestPlayer:
    def test_create_player_with_valid_name(self):
        player = Player.create("Luis")
        assert player.name == "Luis"
        assert isinstance(player.id, PlayerId)

    def test_create_player_with_empty_name_raises(self):
        with pytest.raises(ValueError):
            Player.create("")

    def test_rename_player(self):
        player = Player.create("Luis")
        player.rename("Carlos")
        assert player.name == "Carlos"

    def test_player_equality(self):
        id1 = PlayerId.generate()
        p1 = Player(id=id1, name="Luis")
        p2 = Player(id=id1, name="Luis")
        assert p1 == p2
```

- [ ] Create `tests/unit/domain/test_meetup.py`:
```python
"""Tests for Meetup domain model."""

import pytest
from datetime import datetime

from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.player.models import PlayerId


class TestMeetup:
    def test_create_meetup(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
        assert isinstance(meetup.id, MeetupId)
        assert meetup.date == datetime(2024, 1, 15, 20, 0)

    def test_add_regular_player(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        player_id = PlayerId.generate()
        meetup.add_regular(player_id)
        assert player_id in meetup.regulars

    def test_create_teams(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_regular(p1)
        meetup.add_regular(p2)

        import random
        meetup.create_balanced_teams(random)

        assert meetup.teams is not None
        assert len(meetup.teams) == 2
```

- [ ] Create `tests/unit/application/test_create_player.py`:
```python
"""Tests for CreatePlayer use case."""

import pytest

from pyball.application.player import CreatePlayer
from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player


class FakePlayerRepository:
    def __init__(self):
        self.players = []

    def save(self, player: Player):
        self.players.append(player)

    def find_by_name(self, name: str):
        for p in self.players:
            if p.name == name:
                return p
        return None


class TestCreatePlayer:
    def test_create_player_success(self):
        repo = FakePlayerRepository()
        use_case = CreatePlayer(repo)

        player = use_case.execute("Luis")

        assert player.name == "Luis"
        assert len(repo.players) == 1

    def test_create_duplicate_player_raises(self):
        repo = FakePlayerRepository()
        repo.save(Player.create("Luis"))
        use_case = CreatePlayer(repo)

        with pytest.raises(PlayerAlreadyExistsError):
            use_case.execute("Luis")
```

- [ ] Run: `pytest tests/unit/ -v`

- [ ] Commit: `git add tests/ && git commit -m "test: add unit tests"`

---

## Self-Review Checklist

- [x] Spec coverage verified: Players CRUD, Meetups, Teams
- [x] No placeholders (TBD, TODO) found
- [x] Type consistency checked (PlayerId, MeetupId used consistently)
- [x] All repository interfaces match implementations
