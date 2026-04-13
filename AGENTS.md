# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Implementation Approach

Always use **subagent-driven development** for implementation plans. When the
`writing-plans` skill asks which execution approach to use, always choose subagent-driven
— never ask the user, never choose inline execution.

## Commands

```bash
# Run tests
make test          # or: poetry run nox -e test
make t             # alias

# Run a single test file
poetry run pytest tests/unit/domain/test_meetup.py

# Lint
make lint          # or: poetry run nox -e lint
make l             # alias

# Format
make format        # or: poetry run nox -e format
make f             # alias

# Run via Docker Compose (production)
make up

# Build Docker image
make build
```

## Architecture

Clean architecture with strict layer boundaries:

```
pyball/
  domain/          # Core models and repository interfaces (no dependencies on other layers)
    player/        #   Player entity, PlayerId value object, errors, repository ABC
    meetup/        #   Meetup entity, Team/MatchResult/GoalEvent value objects, MeetupId, errors
  application/     # Use cases — one file per action, injected with repository interfaces
    player/        #   create_player, rename_player, delete_player, change_group
    meetup/        #   create_meetup, add_player, remove_player, create_teams, start_match, finish_match
    container.py   #   Simple DI container — wires repositories to use cases
    fuzzy_match.py #   Shared fuzzy player search utility
  infrastructure/  # Concrete implementations of domain interfaces
    persistence/   #   JsonPlayerRepository, JsonMeetupRepository (file-backed JSON)
    telegram/      #   TelegramMappingStore (telegram_id → player UUID), TelegramMessageStore (message tracking)
    http/app.py    #   FastAPI app — POST /api/match/finish endpoint + serves static/
  bot/             # Telegram bot wiring
    handlers/      #   general.py, player.py, meetup.py — register CommandHandlers
    callbacks.py   #   Inline button callback dispatcher (join/leave meetup)
    formatters.py  #   MarkdownV2 message builders and keyboard factories
    auth.py        #   @authorized decorator — checks settings.telegram.admins_ids
    entrypoint.py  #   create_application() factory
  __main__.py      # Starts both the Telegram polling bot and FastAPI/uvicorn on port 8000
  settings.py      # Loads config.toml + PYBALL_<SECTION>_<KEY> env var overrides
```

**Data flow:** `__main__.py` builds a `Container`, attaches it to `bot_data`, handlers pull use cases from it, use cases interact only with domain repository interfaces, infrastructure implementations handle I/O.

**Two concurrent services** run in a single asyncio loop: the Telegram polling bot and the FastAPI HTTP server (port 8000). The HTTP API is consumed by the `static/index.html` match-tracking UI.

## Configuration

Copy `example.config.toml` to `config.toml` and fill in values. Required fields:
- `telegram.bot_token`
- `telegram.admins_ids`
- `telegram.regulars.chat_id`
- `telegram.substitutes.chat_id`
- `pyball.location`

Any value can be overridden with env var `PYBALL_<SECTION>_<KEY>` (e.g. `PYBALL_TELEGRAM_BOT_TOKEN`). Nested sections use `_` separator (e.g. `PYBALL_TELEGRAM_REGULARS_CHAT_ID`).

## Testing

- Unit tests: `tests/unit/` — mock repositories with in-memory fakes
- Integration tests: `tests/integration/` — exercise JSON persistence against temp directories
- `pytest-asyncio` is used in strict mode (`asyncio_mode = "strict"` in pyproject.toml); async tests must be decorated with `@pytest.mark.asyncio`
- Coverage is reported against the `pyball/` package

## Internationalization

- **Code** (variables, functions, comments, docstrings): always in English
- **Telegram messages** sent to users: always in Spanish

## Code Quality

The `lint` nox session runs all checks in sequence and reports all failures before exiting:
`black --check`, `isort --check`, `pydocstyle`, `pycodestyle` (max-line-length 99), `mypy`, `pylint`.

Line length is **99** characters. pylint must score **10.00/10**.
