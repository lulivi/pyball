# Development Guide

🇬🇧 English | 🇪🇸 [Español](development.es.md)

How PyBall's code is organised: its layers, how a process starts up, and the two runnable
topologies. For setting up a development environment, running the checks, and the commit
and pull request conventions, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Layers

PyBall follows a clean architecture with strict layer boundaries:

```
pyball/
├── domain/            # Core models and repository interfaces — depends on no other layer
│   ├── player/
│   └── meetup/        #   Meetup, Match, Team, ... and the triangular next-round rules
├── application/       # Use cases — one file per action, injected with repository interfaces
│   ├── player/
│   └── meetup/        #   create_meetup, create_teams, finish_match, close_meetup, ...
├── infrastructure/    # Concrete implementations of the domain interfaces
│   ├── persistence/   #   JSON repositories
│   ├── images/        #   Stats image rendering (WeasyPrint + Jinja2)
│   ├── signup/        #   Personal signup codes
│   ├── telegram/      #   Telegram bot, settings, notifications
│   ├── plugins/       #   Plugin API (/api/v1), event log, credentials, supervisor
│   └── http/          #   FastAPI app, routes, token auth, static web pages
├── cmd/               # One entrypoint per topology — its Composition Root
└── settings.py        # AppSettings and the config.toml loader
```

- `domain/` imports nothing from the other layers.
- `application/` holds one use case per file. Shared application pieces live at its top
  level: `bootstrap.py`, the dependency container, the `MatchNotifier` interface, and
  `init_workspace.py` (the `--bootstrap` workspace generator).
- `infrastructure/http/static/` and `static_signup/` are plain HTML and JavaScript, with
  no build step.

Outside `pyball/`:

- `scripts/` — one-off, self-contained data migration scripts. They aren't imported by
  `pyball/`; run one by hand when a stored JSON format changes.
- `docs/` — user-facing documentation, in English and Spanish.

## Startup

`bootstrap_core()` (in `application/bootstrap.py`) loads `AppSettings`, configures logging,
sets the locale and builds the dependency container. Each `cmd/run_*.py` is the
Composition Root for its topology: it calls `bootstrap_core()`, loads any
integration-specific settings, wires the infrastructure components together, and handles
graceful shutdown: plugins start once the HTTP server accepts connections, and stop
first, before the event streams close and the server exits.

Both entrypoints also accept `--bootstrap`, which only generates a deployment workspace
(`config.toml`, `compose.yaml`, `.env`, ...) and exits. It never touches a running app.

## Topologies

One codebase runs as two topologies:

- **`pyball`** (`cmd/run_pyball.py`): FastAPI only. It always serves `/manage` and
  `/match`; `/signup` is opt-in via `enable_web_signup` in `config.toml`.
- **`pyball-telegram`** (`cmd/run_telegram.py`): the Telegram bot plus FastAPI serving
  `/manage` and `/match` (no `/signup`), both in the same asyncio event loop. Only this
  topology needs `python-telegram-bot` installed.

Every feature is reachable from `/manage` and `/match` alone, on either topology. Telegram
and `/signup` are convenience layers over the same use cases, never a requirement: an
admin can always add, remove or move a player between teams from `/manage`, with no
player visiting `/signup` and no Telegram bot configured.

## Plugins

A plugin is a separate program, in any language, declared under `[pyball.plugins.<name>]`.
Both topologies host plugins the same way:

- `PluginSupervisor` runs each one as a child process, restarts it with backoff when it
  exits, and stops it on shutdown.
- `PluginCredentials` gives each plugin a random bearer token at every start, limited to
  its declared scopes.
- `create_plugin_api()` serves the contract at `/api/v1`, a FastAPI sub-application with
  its own OpenAPI schema. Its routes return the models in `plugins/schemas.py` and never
  the presenters `/manage` uses, so `/manage` can change without breaking plugins.
- `EventLogNotifier` writes every `MatchNotifier` event to `data/events.jsonl`, and
  `GET /api/v1/events` serves that log as server-sent events. `pyball-telegram` puts it in
  front of the Telegram notifier through `CompositeMatchNotifier`, so a Telegram failure
  never loses an event.

A change to `plugins/schemas.py` or to a `/api/v1` route is a change to the plugin
contract: keep it backward compatible, or bump to `/api/v2`.

## Match formats

A meetup holds 2 or 3 teams. With 2 teams it is a single classic match, which closes the
meetup on its own result. With 3 teams it is a triangular: the domain computes each next
pairing from a fixed ruleset, and the meetup stays open across rounds until it is closed
explicitly. See [workflow.md](workflow.md) for the full rules and lifecycle.
