# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Gemini, etc. — `CLAUDE.md`
and `GEMINI.md` are symlinks to this file) when working with code in this repository.

PyBall is a self-hosted football (soccer) meetup manager: recurring meetups, balanced
team generation (2-team classic matches or 3-team "triangular" round-robin sessions),
live match tracking, and season stats — via a web UI (`/manage`, `/match`) and an
optional Telegram bot. User-facing documentation (setup, the full application workflow,
data file formats) lives in `docs/` and `README.md`, in English and Spanish
(`*.es.md`) — keep those in sync with this file when you change related behavior.

## Git conventions

### Branches

Work for a GitHub issue goes on `<type>/gh-<n>[-<slug>]`, where `<type>` is `feature`,
`fix` or `docs` and `<n>` is the issue number (e.g. `feature/gh-4-github-conventions`).

### Commit Messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
The optional scope names the area touched (e.g. `match`, `telegram`, `bootstrap`). The last
line of the body references the GitHub issue(s) the commit belongs to, comma-separated
when there are several:

```
type(scope): <description>

[optional body]

[optional footer(s)]
Refs: #<n>[, #<m>...]
```

Types and release impact (the `release` job of the GitHub Actions `ci` workflow tags `main` based on these):

- `feat` → minor release
- `fix`, `perf` → patch release
- `BREAKING CHANGE:` footer or `!` after type/scope (e.g. `feat(match)!:`) → major release
- `build`, `chore`, `ci`, `docs`, `refactor`, `style`, `test` → no release

### Pull Requests

PRs are squash-merged: the PR title becomes the commit subject on `main` (so it must
follow the format above) and the branch's commit messages become its body, carrying
their `Refs:` lines. The PR description includes `Closes #<n>` for each issue it
resolves, so GitHub closes them on merge.

## Commands

```bash
# Run tests (full suite with coverage)
make test          # or: nox -e test
make t             # alias

# Run a single test file or pass pytest flags
nox -e test -- tests/unit/domain/test_meetup.py -v
nox -e test -- tests/unit/domain/test_meetup.py -k test_name -v

# Lint
make lint          # or: nox -e lint
make l             # alias

# Format
make format        # or: nox -e format
make f             # alias

# Build image from source and run it locally via Docker Compose (dev loop only —
# for a real deployment, see docs/setup.md)
make up

# Build the Docker image from source without running it
make build
```

## Architecture

Clean architecture with strict layer boundaries:

```
pyball/
├── domain/                  # Core models and repository interfaces (no deps on other layers)
│   ├── player/
│   └── meetup/
│       ├── models.py              #   Meetup, Match, Team, GoalEvent, MatchResult
│       └── next_round_calculator.py  # Pure rules engine: who plays next in a triangular
├── application/             # Use cases — one file per action, injected with repository interfaces
│   ├── player/
│   ├── meetup/               #   create_meetup, create_teams / create_teams_manually /
│   │                         #   create_teams_algorithms/, assign_teams_by_id,
│   │                         #   start_next_round, finish_match, close_meetup,
│   │                         #   edit_match_result, compute_stats, ...
│   ├── bootstrap.py          #   bootstrap_core() — shared init for all topologies
│   ├── init_workspace.py     #   --bootstrap: generates config.toml/compose.yaml/.env/README.md
│   ├── notifier.py           #   MatchNotifier ABC + NullMatchNotifier
│   ├── container.py          #   Simple DI container (accepts AppSettings)
│   └── fuzzy_match.py
├── infrastructure/          # Concrete implementations of domain interfaces
│   ├── persistence/         #   JsonPlayerRepository, JsonMeetupRepository, LegacyStats
│   ├── images/              #   StatsHtmlRenderer (WeasyPrint + Jinja2)
│   ├── signup/              #   SignupCodeStore — hashed personal signup codes (data/signup/codes.json)
│   ├── telegram/
│   │   ├── settings.py      #     TelegramSettings, TelegramAppSettings, loader
│   │   ├── logging.py       #     TelegramLogHandler, config_telegram_logging()
│   │   ├── bot/
│   │   │   ├── handlers/    #       general, player, meetup handlers
│   │   │   ├── callbacks.py #       Inline button callback dispatcher
│   │   │   ├── auth.py      #       @authorized decorator
│   │   │   └── entrypoint.py #      create_application() factory
│   │   ├── formatters.py
│   │   ├── notifications.py
│   │   ├── mapping.py
│   │   └── message_store.py #     Telegram message-ID tracking (pyball-telegram only)
│   └── http/
│       ├── app.py            #   FastAPI factory (create_app) + _Server
│       ├── auth.py           #   TokenAuthMiddleware (match_token / signup_token / manage_token)
│       ├── links.py          #   MatchLinkBuilder — builds the /match URL
│       ├── presenters.py     #   Domain → JSON response serialisation
│       ├── schemas.py        #   Pydantic request models
│       ├── routes/           #   meetup.py, match.py, player.py, signup.py, static.py
│       ├── static/           #   manage.html/match.html + their JS (no build step)
│       └── static_signup/    #   signup.html + its JS — isolated /signup frontend,
│                              #   mounted only when enable_web_signup is True
├── cmd/
│   ├── run_pyball.py        #   Topology: FastAPI, /signup opt-in (uv run pyball [--bootstrap])
│   └── run_telegram.py      #   Topology: Telegram + FastAPI      (uv run pyball-telegram [--bootstrap])
├── settings.py              #   AppSettings, PyballConfig, Paths, load_app_settings()
└── exceptions.py
```

Other top-level directories: `scripts/` — one-off, self-contained data migration scripts
(not imported by `pyball/`, run manually when a stored JSON schema changes); `docs/` —
user-facing documentation (see the intro above).

**Data flow:** `bootstrap_core()` loads `AppSettings`, configures logging, sets locale, and
builds the `Container`. Each `cmd/run_*.py` is the Composition Root for its topology —
it calls `bootstrap_core()`, loads any integration-specific settings, wires
infrastructure components, and manages graceful shutdown. Both entrypoints also
accept `--bootstrap`, which just generates a deployment workspace and exits (see
`init_workspace.py` and `docs/setup.md`) — it never touches the running app.

**Two topologies, one codebase:**

- **`pyball`** (`uv run pyball`, `run_pyball.py`): FastAPI only — `/manage` and
  `/match` always; `/signup` opt-in via `enable_web_signup` in `config.toml`
  (`signup_token` is wired into `create_app()` regardless, harmless if unused). No
  Telegram.
- **`pyball-telegram`** (`uv run pyball-telegram`, `run_telegram.py`): bot polls
  Telegram, FastAPI serves `/manage` and `/match` on port 8000 (no `/signup`). Both run
  in the same asyncio event loop.

Only `pyball-telegram` requires `python-telegram-bot` to be installed. Every feature is
reachable from `/manage`/`/match` alone on either topology — Telegram and `/signup` are
convenience layers on top of the same use cases, never a requirement for any feature to
function: an admin can always add, remove, or move a player between teams from
`/manage` without a player ever visiting `/signup`, and without a Telegram bot
configured at all.

**Match formats:** a `Meetup` holds 2 or 3 `Team`s and a `matches: list[Match]`. 2 teams
means a single classic match that closes the meetup on its own result; 3 teams means a
triangular — `next_round_calculator.py` computes each subsequent pairing automatically
per a fixed ruleset, and the meetup stays open across rounds until explicitly closed
(`close_meetup`/`CloseMeetup`). See `docs/workflow.md` for the full rules and lifecycle.

## Package Management

This project uses **uv** for dependency management.

```bash
# Install with Telegram support (default for development)
uv sync --extra telegram

# Install without Telegram (pyball topology)
uv sync

# Install all extras including dev tools
uv sync --all-extras

# Run topologies
uv run pyball            # FastAPI only, /signup opt-in via config
uv run pyball-telegram   # Telegram + FastAPI
```

## Configuration

Run `uv run pyball --bootstrap` or `uv run pyball-telegram --bootstrap` to generate a
`config.toml` template (there's no
static `example.config.toml` to copy — the template is generated code, in
`application/init_workspace.py`, kept in sync with `PyballConfig` and
`TelegramSettings`). **Do not add a config key to `settings.py` or
`telegram/settings.py` without also adding it to `init_workspace.py`'s templates and to
`docs/setup.md`'s tables** — those three are the only places a key is documented, and
they drift independently if only one is updated.

Any value can be overridden with env var `PYBALL_<SECTION>_<KEY>` (e.g.
`PYBALL_TELEGRAM_BOT_TOKEN`). The `pyball.` prefix is stripped for env vars, so
`pyball.core.location` becomes `PYBALL_CORE_LOCATION`. See `docs/setup.md` for the full,
current table of every key.

## Testing

- Unit tests: `tests/unit/` — mock repositories with in-memory fakes
- Integration tests: `tests/integration/` — exercise JSON persistence against temp directories
- `pytest-asyncio` is used in strict mode (`asyncio_mode = "strict"` in pyproject.toml); async tests must be decorated with `@pytest.mark.asyncio`
- Coverage is reported against the `pyball/` package

## Internationalization

- **Code** (variables, functions, comments, docstrings): always in English
- **User-facing text** — Telegram messages and the `/manage`/`/match` web UI alike:
  always in Spanish
- **`docs/` and `README.md`**: written in both languages as parallel files (`foo.md` in
  English, `foo.es.md` in Spanish) — update both when either changes

## Code Quality

The `lint` nox session runs all checks in sequence and reports all failures before exiting:
`black --check`, `isort --check`, `pydocstyle`, `pycodestyle` (max-line-length 99), `mypy`, `pylint`.

Line length is **99** characters. pylint must score **10.00/10**.

## Code Organization — Top-Bottom Ordering

Apply the **two-zone top-bottom** pattern in every Python module:

1. **Zone 1 — High-level / public** (top): entry points, main classes, public functions, `setup_*` registrars.
2. **Zone 2 — Low-level / private** (bottom): helper functions and methods prefixed with `_`.

Within each zone, apply the same rule recursively (callers above callees).

**Rules:**
- The main class in a module goes at the top, even if it calls private module-level helpers defined below it.
- `from __future__ import annotations` must be added to any file where moving a class or type to the top would create a forward-reference error.
- Module-level `setup_*` / factory / entry-point functions go above the handlers or objects they register.
- Do not mix the two zones — all private helpers must appear after all public items.

**Example ordering for a handler module:**
```
setup_handlers()          ← Zone 1: registrar
public_handler_a()        ← Zone 1: public handler
public_handler_b()        ← Zone 1: public handler
_helper_for_a()           ← Zone 2: private helper
_helper_for_b()           ← Zone 2: private helper
_shared_utility()         ← Zone 2: private utility
```
