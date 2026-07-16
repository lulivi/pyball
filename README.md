# PyBall

🇬🇧 English | 🇪🇸 [Español](README.es.md)

Self-hosted football (soccer) meetup manager: track recurring matches, build balanced
teams, record results, and see season stats — from a phone browser, optionally paired
with a Telegram bot.

## Running PyBall

Most people just want to run the app. All you need is Docker.

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap
# or, for the self-service /signup page:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-web --bootstrap
# or, for Telegram:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-telegram --bootstrap

# edit config.toml with your settings, then:
docker compose up -d
```

`--bootstrap` generates `config.toml`, `compose.yaml`, `.env`, and the `data/`/`logs/`
directories in the current folder — see **[docs/setup.md](docs/setup.md)** for the full
walkthrough: choosing a topology, configuring `config.toml`, what `/manage` and `/match`
are for, and access tokens.

- **[docs/setup.md](docs/setup.md)** — install, configure, and run PyBall.
- **[docs/workflow.md](docs/workflow.md)** — how a meetup goes from creation to
  finished stats, including the classic (2-team) and triangular (3-team) match formats.
- **[docs/data-directory.md](docs/data-directory.md)** — the directory structure PyBall
  creates and the JSON file formats it uses.

## Development

Building PyBall from source, running its test suite, or contributing to it needs more
than Docker.

### Prerequisites

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) for dependency management
- [nox](https://nox.thea.codes/en/stable/) for automation

### Install

```bash
uv sync --all-extras
```

### Run from source

```bash
uv run pyball --bootstrap       # first run only, generates config.toml
uv run pyball                   # /manage + /match, no Telegram, no /signup

uv run pyball-web --bootstrap
uv run pyball-web               # /manage + /match + /signup, no Telegram

uv run pyball-telegram --bootstrap
uv run pyball-telegram          # /manage + /match + Telegram bot
```

### Checks

```bash
make format      # Format code (black + isort)
make lint        # Run all lint checks
make test        # Run tests with coverage
```

### Local Docker loop

```bash
make up           # builds the image from source and runs it via Docker Compose
```

## Architecture

Clean architecture with strict layer boundaries:

- **domain/** — Core models and repository interfaces
- **application/** — Use cases with injected repository interfaces
- **infrastructure/** — Concrete implementations (JSON persistence, Telegram, HTML rendering)

## License

MIT
