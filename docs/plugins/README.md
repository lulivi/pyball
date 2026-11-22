# Plugins

🇬🇧 English | 🇪🇸 [Español](README.es.md)

A plugin is an optional, long-running program, written in any language, that extends
PyBall without touching its code. It runs for as long as PyBall does, reacting to the
event stream or keeping its own schedule: a job that runs once and exits belongs in cron.

A plugin is either **bundled**, shipped inside the PyBall images, or your own program in
the workspace's `plugins/` folder, which the generated `compose.yaml` mounts at
`/pyball/plugins`. Either way it runs only once `config.toml` declares it (see
[`[pyball.plugins.<name>]`](../setup.md#pyballpluginsname--optional-plugins)). Then start
PyBall as usual: it is still one command.

## Bundled plugins

| Plugin | What it does | `command` |
|---|---|---|
| [siesta](siesta/README.md) | Decides fairly who sits out when more players sign up than a meetup takes, and builds the teams | `["siesta", "run"]` |

## How PyBall runs a plugin

PyBall runs every declared plugin as a child process, from the workspace directory:

- **Start:** once the web server is up, with three environment variables:
  `PYBALL_API_URL` (the plugin API, e.g. `http://127.0.0.1:8000/api/v1`),
  `PYBALL_API_TOKEN` (the plugin's own token, new at every start) and
  `PYBALL_PLUGIN_NAME`.
- **State:** a plugin keeps whatever it must remember, such as the last event it
  handled, in `data/plugins/<name>/`, creating the folder itself. That folder sits inside
  the mounted `data/`, so it survives container restarts and goes into your backups.
- **Output:** whatever the plugin prints goes to PyBall's log, under
  `pyball.plugins.<name>`.
- **Crashes:** a plugin that exits is started again after 1 s, then 2 s, 4 s, ... up to
  60 s; one that ran for a minute starts again after 1 s. PyBall itself keeps running.
- **Shutdown:** PyBall sends `SIGTERM` to each plugin and, 10 s later, `SIGKILL` to any
  still running.

## The plugin API

A plugin talks to PyBall only through `PYBALL_API_URL`, sending
`Authorization: Bearer $PYBALL_API_TOKEN`. Each call is one logical action and records
one event. The full contract, with every request and response shape, is the OpenAPI
schema at `/api/v1/openapi.json`, browsable at `/api/v1/docs`.

| Call | Scope | What it does |
|---|---|---|
| `GET /players` | `players:read` | Every player |
| `GET /meetups/active` | `meetups:read` | The active meetup, with its capacity and substitute search |
| `POST /meetups` | `meetups:write` | Create a meetup; `location` and `capacity` are optional |
| `DELETE /meetups/{id}` | `meetups:write` | Cancel the active meetup |
| `PUT` / `DELETE /meetups/{id}/players/{player_id}` | `meetups:write` | Add or remove a player |
| `PUT /meetups/{id}/lineup` | `meetups:write` | Set the roster and, with `team_algorithm` (`balanceado` or `random`), make the teams |
| `PUT /meetups/{id}/capacity` | `meetups:write` | Change the capacity |
| `POST` / `DELETE /meetups/{id}/substitute-search` | `meetups:write` | Open or close the substitute search |
| `GET /events` | `meetups:read` | The event stream, below |

## The event stream

`GET /api/v1/events` is a stream of
[server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html).
Each event has an `id`, its type as `event`, and a JSON `data` with the meetup as it was
right after (see [`data/events.jsonl`](../data-directory.md#dataeventsjsonl) for the types
and fields). To miss nothing, a plugin keeps the last `id` it handled and reconnects
with `Last-Event-ID: <id>` (or `?after=<id>`): it receives every later event, in order
and without duplicates, then new ones as they happen. `?after=0` replays the whole log;
with neither, the stream starts with the next event. An idle stream sends a comment
every 15 s.
