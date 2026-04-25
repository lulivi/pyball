# PyBall v4 Design

## Overview

PyBall is a Telegram bot for managing football meetups. This version implements a clean architecture with Domain-Driven Design principles while maintaining simplicity through a modular monolith approach.

## Architecture

### Package Structure

```
pyball/
├── __main__.py           # Entry point
├── __init__.py
├── settings.py           # Configuration (tokens, paths)
├── domain/               # Pure business logic (no Telegram)
│   ├── player/
│   │   ├── models.py     # Player, PlayerId
│   │   ├── errors.py
│   │   └── repository.py
│   ├── meetup/
│   │   ├── models.py     # Meetup, Team
│   │   ├── errors.py
│   │   └── repository.py
│   └── match/
│       ├── models.py
│       ├── errors.py
│       └── repository.py
├── application/          # Use cases
│   ├── player/
│   ├── meetup/
│   └── __init__.py
├── infrastructure/
│   ├── json_repository.py
│   └── storage.py
└── bot/                  # Telegram layer (thin)
    ├── entrypoint.py
    ├── handlers/
    ├── keyboards.py
    └── mappers.py        # Player ↔ Telegram mappings
```

## Domain Layer

### Player Aggregate

**Models:**
- `PlayerId`: Value object wrapping UUID string
- `Player`: Entity with `id: PlayerId` and `name: str`

**Repository Interface:**
```python
class PlayerRepository(Protocol):
    def save(self, player: Player) -> None: ...
    def find_by_id(self, id: PlayerId) -> Player | None: ...
    def find_all(self) -> list[Player]: ...
    def delete(self, id: PlayerId) -> None: ...
```

### Meetup Aggregate

**Models:**
- `Meetup`: Entity with `id`, `date`, `regulars: list[PlayerId]`, `substitutes: list[PlayerId]`, `teams: list[Team] | None`
- `Team`: Value object with `name` and `players: list[PlayerId]`

**Repository Interface:**
```python
class MeetupRepository(Protocol):
    def save(self, meetup: Meetup) -> None: ...
    def find_by_id(self, id: MeetupId) -> Meetup | None: ...
    def find_by_date(self, date: date) -> Meetup | None: ...
    def find_all(self) -> list[Meetup]: ...
```

### Match Aggregate

For future extension (recording match results, goals).

## Application Layer

### Player Use Cases
- `CreatePlayer(name: str) -> Player`
- `RenamePlayer(player_id: PlayerId, new_name: str) -> Player`
- `DeletePlayer(player_id: PlayerId) -> None`

### Meetup Use Cases
- `CreateMeetup(date: datetime) -> Meetup`
- `AddPlayerToMeetup(meetup_id: MeetupId, player_id: PlayerId, role: Regular | Substitute) -> Meetup`
- `RemovePlayerFromMeetup(meetup_id: MeetupId, player_id: PlayerId) -> Meetup`
- `CreateTeams(meetup_id: MeetupId) -> Meetup` (random balanced teams)

## Infrastructure Layer

### JSON Storage

Files stored in `data/` directory:
- `data/players.json` - All players
- `data/meetups/{YYYY-MM-DD}.json` - Meetups by date
- `data/bot/mappings.json` - Telegram ↔ Player mappings

**players.json:**
```json
{
  "players": [
    {"id": "uuid", "name": "Luis"}
  ]
}
```

**meetups/2024-01-15.json:**
```json
{
  "id": "uuid",
  "date": "2024-01-15T20:00",
  "regulars": ["player-uuid"],
  "substitutes": [],
  "teams": null
}
```

**bot/mappings.json:**
```json
{
  "player_telegram": {
    "player-uuid": 123456789
  }
}
```

## Bot Layer

Thin layer responsible only for:
- Receiving Telegram updates
- Mapping telegram_id → player_id
- Invoking application use cases
- Formatting responses for Telegram

**Key principle:** Telegram is an input mechanism, not part of the domain.

## SOLID Principles Applied

| Principle | Application |
|-----------|-------------|
| **S** - Single Responsibility | Each module has one clear purpose |
| **O** - Open/Closed | Extend via repositories, not modification |
| **L** - Liskov Substitution | Repository interfaces allow any implementation |
| **I** - Interface Segregation | Separate repositories per aggregate |
| **D** - Dependency Inversion | Bot depends on interfaces, not implementations |

## Testing Strategy

- **Domain layer:** Pure unit tests, no I/O
- **Application layer:** Unit tests with fake repositories
- **Infrastructure layer:** Integration tests with real JSON files
- **Bot layer:** Handlers tested with mocks

## Initial Scope

1. Player management (CRUD)
2. Meetup creation and management
3. Add/remove players (regulars & substitutes)
4. Random team generation
5. Display meetup status

Future: Match results, statistics, goals.
