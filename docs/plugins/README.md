# Plugins

🇬🇧 English | 🇪🇸 [Español](README.es.md)

A plugin is an optional, long-running program, written in any language, that extends
PyBall without touching its code. It runs for as long as PyBall does, reacting to the
event stream or keeping its own schedule: a job that runs once and exits belongs in cron.

A plugin is either **bundled**, shipped inside the PyBall image, or your own program in
the workspace's `plugins/` folder, which the generated `compose.yaml` mounts at
`/pyball/plugins`. Either way it runs only once `config.toml` declares it (see
[`[pyball.plugins.<name>]`](../setup.md#pyballpluginsname--optional-plugins)). Then start
PyBall as usual: it is still one command.

## Bundled plugins

| Plugin | What it does | `command` |
|---|---|---|
| [activity](activity/README.md) | Posts who joins or leaves a meetup, and each meetup created, closed or cancelled, to a Telegram chat | `["activity"]` |
| [siesta](siesta/README.md) | Decides fairly who sits out when more players sign up than a meetup takes, and builds the teams | `["siesta", "run"]` |
| [telegram](telegram/README.md) | The Telegram bot: callups with join/leave buttons, the substitutes callup, results, stats and admin commands | `["telegram"]` |

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
`Authorization: Bearer $PYBALL_API_TOKEN`. Each write is one logical action and records
one event. Each team of a meetup carries the club's `color` and `emoji` for its position.
The full contract, with every request and response shape and the data of each
event, is the OpenAPI schema at `/api/v1/openapi.json`, browsable at `/api/v1/docs`. The
same schema is committed in the repository as
[`plugins/openapi.json`](../../plugins/openapi.json), so a plugin can generate a client
from it or check its own types against it without a running PyBall.

| Call | Scope | What it does |
|---|---|---|
| `GET /settings` | any | The club's `display_date_format` and `locale` |
| `GET /players` | `players:read` | Every player |
| `GET /meetups/active` | `meetups:read` | The active meetup, with its capacity and substitute search |
| `GET /meetups?date=<date>` | `meetups:read` | The meetup at that date, as a list of zero or one |
| `GET /meetups/{id}/summary` | `meetups:read` | The result summary of a closed meetup, the one `/manage` copies |
| `GET /stats.png?scope=season` | `meetups:read` | The stats image of the season, or of all time with `scope=alltime` |
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
