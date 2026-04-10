# PyBall Manager

Telegram bot for managing non-US football meetups - players, teams, call-ups, and scheduling.

## Execution Preference

- **Always use subagent-driven development** for implementation plans (recommended approach)

## Tech Stack

- **Python**: 3.11+
- **Telegram Bot**: python-telegram-bot 22.x
- **Data Validation**: Pydantic 2.x
- **Testing**: pytest, pytest-asyncio, nox
- **Code Quality**: black, isort, mypy, pylint, pydocstyle

## Commands

- `make up` - Run bot via Docker Compose
- `make run` - Run bot container once
- `make test` / `make t` - Run tests via nox
- `make format` / `make f` - Format code
- `make build` - Build Docker image
- `make publish` - Build and push Docker image

## Code Quality

Run via `nox` (sessions: lint, test, format):
```bash
poetry run nox -e lint
poetry run nox -e test
poetry run nox -e format
```

## Architecture

- `pyball/domain/` - Domain models (Player, Meetup)
- `pyball/application/` - Use cases (add_player, create_meetup, etc.)
- `pyball/infrastructure/` - Telegram API, JSON persistence
- `pyball/bot/` - Telegram handlers and entrypoint
- `pyball/settings.py` - Configuration loading from config.toml

## Configuration

See `config.toml` for settings. Environment variables override config values using pattern `PYBALL_<SECTION>_<KEY>` (e.g., `PYBALL_TELEGRAM_BOT_TOKEN`).

## Testing

Tests in `tests/unit/` and `tests/integration/`. Run with:
```bash
poetry run nox -e test
```