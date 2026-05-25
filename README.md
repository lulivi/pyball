# PyBall Manager

Telegram bot for managing football meetups, teams, and player statistics.

## Quick Start

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) for dependency management
- [nox](https://nox.thea.codes/en/stable/) for automation

### Configuration

Copy the example config and fill in your values:

```bash
cp example.config.toml config.toml
```

Edit `config.toml` with your Telegram bot token, admin IDs, and chat IDs. Any value can be overridden with environment variables using the `PYBALL_<SECTION>_<KEY>` format (e.g. `PYBALL_TELEGRAM_BOT_TOKEN`).

### Install Dependencies

```bash
uv sync --all-extras
```

### Run

```bash
make up
```

This builds and starts the Telegram topology (bot + FastAPI on port 8000) inside Docker.

Or run directly without Docker:

```bash
uv run pyball-tg   # Telegram + FastAPI (port 8000)
uv run pyball-web  # FastAPI only (port 8000) — no Telegram required
```

## Development

```bash
make format      # Format code (black + isort)
make lint        # Run all lint checks
make test        # Run tests with coverage
```

## Architecture

Clean architecture with strict layer boundaries:

- **domain/** — Core models and repository interfaces
- **application/** — Use cases with injected repository interfaces
- **infrastructure/** — Concrete implementations (JSON persistence, Telegram, HTML rendering)

## License

MIT
