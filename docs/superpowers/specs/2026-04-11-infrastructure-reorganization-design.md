# Infrastructure Layer Reorganization Design

## Overview
Refactor the infrastructure layer to improve code organization and visual clarity by splitting mixed files into logical subfolders.

## Current Structure

```
infrastructure/
├── __init__.py
├── json_repository.py      # Contains player AND meetup repositories
├── telegram_store.py      # Telegram message tracking
└── telegram_mapping.py    # Telegram ID to player ID mapping
```

## Proposed Structure

```
infrastructure/
├── __init__.py
├── persistence/
│   ├── __init__.py
│   ├── player_repository.py
│   └── meetup_repository.py
└── telegram/
    ├── __init__.py
    ├── message_store.py
    └── mapping.py
```

## Changes

1. **Split `json_repository.py`** into:
   - `persistence/player_repository.py` - `JsonPlayerRepository`
   - `persistence/meetup_repository.py` - `JsonMeetupRepository`

2. **Move Telegram files** into `telegram/` subfolder:
   - `telegram_store.py` → `telegram/message_store.py`
   - `telegram_mapping.py` → `telegram/mapping.py`

3. **Update imports** in:
   - `infrastructure/__init__.py`
   - `application/container.py`
   - Any other files importing from infrastructure

## Rationale

- **Separation of concerns**: Domain persistence (repositories) vs Telegram-specific infrastructure
- **Scalability**: New persistence implementations can go in `persistence/`, new Telegram features in `telegram/`
- **Visual clarity**: Each folder has a single, well-defined purpose