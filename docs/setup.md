# Setup Guide

🇬🇧 English | 🇪🇸 [Español](setup.es.md)

This guide covers installing, configuring, and running PyBall as an end user. If you
want to build PyBall from source or contribute to it, see the
[contributing guide](../CONTRIBUTING.md) instead.

This guide assumes Linux with Docker installed — the simplest, most-tested way to
run PyBall. Installing on a Windows PC instead? Follow this guide as written, but
read [Running on Windows (WSL2)](#running-on-windows-wsl2) before step 1.

## 1. Choose a topology

PyBall ships as two Docker images, built from the same codebase:

| Image | What it runs | Needs a Telegram bot? |
|---|---|---|
| `lulivi/pyball` | FastAPI — `/manage`, `/match`, and an optional self-service `/signup` (see below) | No |
| `lulivi/pyball-telegram` | Telegram bot + FastAPI (`/manage` and `/match`) | Yes |

Every feature — creating meetups, building teams (classic or triangular), tracking a
match, closing a triangular session, viewing stats — is reachable from `/manage` and
`/match` on either image; Telegram and `/signup` are convenience layers on top, never a
requirement. If your group doesn't use Telegram, use `pyball`: set `enable_web_signup =
true` in `config.toml` if you want players to join or leave a meetup themselves from a
personal code at `/signup` (see
[Application Workflow](workflow.md#self-service-signup-via-signup)) without touching
`/manage`, or leave it `false` (the default) to keep signup an admin-only,
`/manage`-driven task. Use `pyball-telegram` if you want meetups posted to a group chat
automatically, admin commands from Telegram, and reactions/notifications in the chat.

## 2. Bootstrap a workspace

Pick an empty directory for this instance's config and data, then run:

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap
# or, for Telegram:
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-telegram --bootstrap
```

This creates, in the current directory:

```
config.toml     # your settings — edit this next
compose.yaml    # docker compose service definition, pinned to the image you bootstrapped
.env            # UID/GID/PORT/TAG used by compose.yaml
README.md       # a short pointer back to this guide
data/           # JSON data files (see docs/data-directory.md)
logs/           # application logs
```

`--bootstrap` refuses to run if any of `config.toml`, `compose.yaml`, or `.env` already
exist in the target directory, so it's safe to re-run — it won't overwrite your setup.

## 3. Configure `config.toml`

Every key can also be set with an environment variable, `PYBALL_<SECTION>_<KEY>`
(e.g. `PYBALL_CORE_LOCATION`, `PYBALL_TELEGRAM_BOT_TOKEN`) — useful for keeping secrets
out of `config.toml` or overriding a value per-deployment without editing the file.

### `[pyball.core]` — all topologies

| Key | Description | Default |
|---|---|---|
| `location` | Default meetup location | *(required)* |
| `name` | Instance name shown in the UI | *(required)* |
| `default_week_day` | Default day (`monday`–`sunday`) for new meetups | `wednesday` |
| `default_hour` | Default start time (`HH:MM`) | `20:00` |
| `meetup_capacity` | Players a new meetup plays with; each meetup's capacity can then be changed from `/manage` | `10` |
| `display_date_format` | Date format used in messages | `%Y-%m-%d %H:%M` |
| `team_colors` | Two or three color names: the first two are the classic-match teams, the third is only used for triangulars (auto-filled if you list just two) | `["blanco", "negro", "rojo"]` |
| `base_url` | Public URL used to build the `/match` link | *(required)* |
| `api_port` | HTTP server port | `8000` |
| `locale` | Locale used to sort player names | `es_ES.UTF-8` |
| `data_dir` | Directory for JSON data files; a relative path starts from the folder holding `config.toml` | `data` |
| `match_token` | Access token for `/match` only (optional, see [Access tokens](#6-access-tokens)) | *(empty)* |
| `manage_token` | Access token for everything, including `/manage` (optional) | *(empty)* |
| `enable_web_signup` | Enables the self-service `/signup` page | `false` |
| `signup_token` | Access token for `/signup` only (optional; only relevant if `enable_web_signup` is true, harmless if left unset) | *(empty)* |
| `theme_color` | PWA theme/background color | `#0f172a` |
| `icons_dir` | Custom PWA icons directory (optional); a relative path starts from the folder holding `config.toml` | *(empty)* |

Available team colors: `blanco` `negro` `rojo` `naranja` `amarillo` `verde` `azul`
`morado` `marron`.

### `[pyball.telegram]` and sub-sections — `pyball-telegram` only

These are ignored by `pyball` — see
[Telegram config is bot-only](data-directory.md#telegram-config-is-bot-only) for why.

| Key | Description | Required |
|---|---|---|
| `telegram.bot_token` | Bot token from [@BotFather](https://t.me/BotFather) | **Yes** |
| `telegram.admins_ids` | Telegram user IDs allowed to run admin commands | **Yes** |
| `telegram.regulars.meetups.chat_id` | Chat for meetup callup + corrected-result messages (negative for groups) | **Yes** |
| `telegram.regulars.meetups.message_thread_id` | Forum topic for those messages (empty = none) | No |
| `telegram.regulars.stats.chat_id` | Chat for post-match stats + `/meetup_stats` (`0` / omit disables stats posting) | No |
| `telegram.regulars.stats.message_thread_id` | Forum topic for stats (empty = none) | No |
| `telegram.substitutes.meetups.chat_id` | Chat for the substitutes callup message (negative for groups) | **Yes** |
| `telegram.substitutes.meetups.message_thread_id` | Forum topic for the substitutes message (empty = none) | No |
| `telegram.management.logging.chat_id` | Operational log channel (`0` / omit to disable) | No |
| `telegram.management.logging.message_thread_id` | Forum topic for log records (empty = none) | No |
| `telegram.management.activity.chat_id` | Meetup activity feed chat — joins, leaves, created/closed/cancelled (`0` / omit to disable) | No |
| `telegram.management.activity.message_thread_id` | Forum topic for the activity feed (empty = none) | No |

To find a chat ID: add the bot to the group, send any message, then check
`https://api.telegram.org/bot<TOKEN>/getUpdates` for the `chat.id` field.

Each of these can point at the same or a different group/topic. Env overrides
follow `PYBALL_<PATH>_<KEY>`, e.g.
`PYBALL_TELEGRAM_MANAGEMENT_ACTIVITY_CHAT_ID`.

`deploy/deploy.sh` sends its own deploy notifications with the bot token, chat and
forum topic in the `DEPLOY_NOTIFY_TOKEN`, `DEPLOY_NOTIFY_CHAT_ID` and
`DEPLOY_NOTIFY_THREAD_ID` GitHub secrets — point them at the same chat and topic as
`telegram.management.logging`. Without `DEPLOY_NOTIFY_TOKEN`, deploys send no
notifications.

### `[pyball.plugins.<name>]` — optional plugins

One table per plugin, named after it. Both topologies run them (see
[Plugins](#8-plugins)). These tables have no env overrides.

| Key | Description | Required |
|---|---|---|
| `command` | Program and arguments that start the plugin, run from the workspace, e.g. `["./plugins/example-plugin", "--verbose"]` | **Yes** |
| `scopes` | What the plugin may do through the plugin API: any of `players:read`, `players:write`, `meetups:read` (includes the event stream), `meetups:write` | No (none) |

## 4. Start the app

```bash
docker compose up -d
docker compose logs -f
```

Once running, open `http://<host>:<PORT>/manage` in a browser (the port is whatever you
set in `.env`).

## 5. `/manage` vs `/match`

PyBall's web UI is two pages:

- **`/manage`** — the admin page. Paste a callup, add/remove players, generate teams
  (classic or triangular), edit teams manually, regenerate, close a triangular session,
  and view/share the summary of the last finished match.
- **`/match`** — the live scoreboard. Shows the current pending match, lets you register
  goals/assists, and finish the match. Meant to be left open on a phone or tablet during
  the session — it auto-loads whichever match is currently active, no manual setup
  needed once you're past the token prompt (below).

With `enable_web_signup = true` there's also `/signup`, a self-service page for
players — see
[Self-service signup via `/signup`](workflow.md#self-service-signup-via-signup).

See [docs/workflow.md](workflow.md) for the full step-by-step flow.

## 6. Access tokens

`match_token`, `signup_token`, and `manage_token` protect the app when it's exposed
beyond your own private network (e.g. through a reverse proxy on the public internet) —
without them, `/manage`, `/match`, and `/signup` are open to anyone who reaches the URL.
If all three are left empty, no authentication is enforced at all (fine for a private
network you already trust). How you expose the app publicly (reverse proxy, VPN, tunnel,
etc.) is up to you — these tokens work the same regardless.

| Path | Required token |
|---|---|
| `/`, static assets, PWA manifests | None (always public) |
| `/match`, `GET /api/match/active`, `POST /api/match/finish` | `match_token` **or** `manage_token` |
| `/signup` and `/api/signup/*` (only when `enable_web_signup` is true) | `signup_token` **or** `manage_token` |
| `/api/v1/*` (the plugin API) | `Authorization: Bearer` with a plugin's own token **or** `manage_token` — see [Plugins](#8-plugins) |
| `/manage` and everything else under `/api/*` | `manage_token` only |

Give the scoreboard-only `match_token` to a device that should only ever see `/match`
(e.g. a tablet mounted at the pitch), the `signup_token` to players (if `/signup` is
enabled), and the `manage_token` to admins. Visiting a URL with `?token=<value>` once validates it
and sets an `HttpOnly` cookie that lasts a year — no need to pass the token again after
that on the same device/browser.

`signup_token` only gates the `/signup` page itself, like a site password shared with
everyone who's allowed to use it; once inside, each player additionally identifies
themselves with their own personal signup code (see
[Application Workflow](workflow.md#self-service-signup-via-signup)) — the two are
independent layers, and neither substitutes for the other.

## 7. Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version instead of always tracking `latest` by setting `TAG=4.13.0` in
`.env`.

## 8. Plugins

A plugin is an optional, long-running program, written in any language, that extends
PyBall without touching its code. It runs for as long as PyBall does, reacting to the
event stream or keeping its own schedule: a job that runs once and exits belongs in cron. Declare it in `config.toml` (see
[`[pyball.plugins.<name>]`](#pyballpluginsname--optional-plugins)) and put the program
in the workspace's `plugins/` folder, which the generated `compose.yaml` mounts at
`/pyball/plugins`. Then start PyBall as usual: it is still one command.

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

### The plugin API

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

### The event stream

`GET /api/v1/events` is a stream of
[server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html).
Each event has an `id`, its type as `event`, and a JSON `data` with the meetup as it was
right after (see [`data/events.jsonl`](data-directory.md#dataeventsjsonl) for the types
and fields). To miss nothing, a plugin keeps the last `id` it handled and reconnects
with `Last-Event-ID: <id>` (or `?after=<id>`): it receives every later event, in order
and without duplicates, then new ones as they happen. `?after=0` replays the whole log;
with neither, the stream starts with the next event. An idle stream sends a comment
every 15 s.

## Running on Windows (WSL2)

PyBall's Docker images are Linux containers; on Windows the simplest way to run
them is inside WSL2 (Windows Subsystem for Linux), where the rest of this guide
applies unchanged.

1. **Enable WSL2.** Open PowerShell as Administrator and run:

   ```powershell
   wsl --install
   ```

   This installs WSL2 and a default Ubuntu distribution. Reboot if prompted.

2. **Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).**
   Its installer detects WSL2 and enables the WSL2 integration by default — no
   manual Docker Engine install inside the distro needed.

3. **Open the "Ubuntu" app** from the Start menu — this is a regular WSL2 terminal.
   Docker Desktop shares its daemon with it, so every `docker`/`docker compose`
   command in this guide works exactly as written from here, starting at
   [step 2, "Bootstrap a workspace"](#2-bootstrap-a-workspace).

4. If the app needs to stay reachable (e.g. during a match), disable Windows sleep
   for that time: Settings → System → Power & battery → Screen and sleep.

See [docs/deployment.md](deployment.md) for reaching this instance from outside the
PC's local network.

## Next steps

- [docs/workflow.md](workflow.md) — the full meetup lifecycle: creating a meetup,
  building teams, the classic vs triangular formats, tracking a match, and stats.
- [docs/data-directory.md](data-directory.md) — what's inside `data/`, and the JSON
  format of each file.
- [docs/deployment.md](deployment.md) — reaching your instance from outside your
  local network (no VPS? see the on-demand ngrok option).
