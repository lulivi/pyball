# AGENTS.md

Guidance for AI coding agents working in this repository. `CLAUDE.md` and `GEMINI.md` are
symlinks to this file.

PyBall is a self-hosted football (soccer) meetup manager: recurring meetups, balanced team
generation, live match tracking and season stats, through a web UI (`/manage`, `/match`)
and an optional Telegram bot. [docs/development.md](docs/development.md) describes the
architecture; the rest of `docs/` and `README.md` are the user documentation.

## Commands

```bash
uv sync                                          # install, dev tools included
make t                                           # tests, with coverage
make l                                           # lint (black, isort, pydocstyle, mypy, ...)
make f                                           # format
make plugins-check                               # format, lint and tests of plugins/*, clients/*
make openapi                                     # regenerate plugins/openapi.json
uvx nox -e test -- tests/unit/<path>.py -k <name> -v # one test file or test
```

Lint must pass with lines of at most 99 characters and a pylint score of 10.00/10.

## Git

Before creating a branch, committing or opening a pull request, read
[CONTRIBUTING.md](CONTRIBUTING.md) and follow its branch, commit and pull request
conventions: the release automation tags `main` from the commit types.

## Architecture rules

- `domain/` depends on no other layer.
- `application/` holds one use case per file, injected with repository interfaces.
- `cmd/run_pyball.py` is the Composition Root: wiring lives there, never in `domain/` or
  `application/`. Integrations are plugins on `/api/v1`.
- Every feature is reachable from `/manage` and `/match` alone. Telegram is a convenience
  layer over the same use cases, so a feature works with no Telegram bot configured.

## Code organization

Order every Python module in two zones, callers above callees within each:

1. **Public** (top): entry points, the main class, public functions, `setup_*` registrars
   and factories above whatever they register.
2. **Private** (bottom): every `_`-prefixed helper, after all public items.

The main class goes at the top even when it calls private helpers below it; add
`from __future__ import annotations` when that creates a forward reference.

## Tests

- Unit tests (`tests/unit/`) replace repositories with in-memory fakes; integration tests
  (`tests/integration/`) exercise JSON persistence in temp directories.
- `pytest-asyncio` runs in strict mode: decorate every async test with
  `@pytest.mark.asyncio`.

## Language

- Code, comments and docstrings: English.
- User-facing text, in Telegram messages and the web UI alike: Spanish.
- `docs/`, `README.md` and `CONTRIBUTING.md` come as parallel files, `foo.md` in English
  and `foo.es.md` in Spanish: update both together.
- A change to behaviour that `docs/` describes updates those docs in the same change.

## Skills

Skills live in `.agents/skills/`. Read the skill before the change it covers:

- **Config keys** — adding, renaming or removing a `config.toml` key changes the settings
  class, the `init_workspace.py` template and the `docs/setup.md` tables together:
  [add-config-key](.agents/skills/add-config-key/SKILL.md).
- **Plugins** — a new bundled plugin, or a new integration (WhatsApp, Slack, ...), follows
  [Bundled plugins](docs/development.md#bundled-plugins).
