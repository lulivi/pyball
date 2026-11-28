# Setup Guide

🇬🇧 English | 🇪🇸 [Español](setup.es.md)

This guide covers installing, configuring, and running PyBall as an end user. If you
want to build PyBall from source or contribute to it, see the
[contributing guide](../CONTRIBUTING.md) instead.

This guide assumes Linux with Docker installed — the simplest, most-tested way to
run PyBall. Installing on a Windows PC instead? Follow this guide as written, but
read [Running on Windows (WSL2)](#running-on-windows-wsl2) before step 1.

## 1. What PyBall runs

PyBall ships as one Docker image, `lulivi/pyball`: the web server with `/manage` and
`/match`, plus the bundled plugins, which run
only once `config.toml` declares them.

Every feature — creating meetups, building teams (classic or triangular), tracking a
match, closing a triangular session, viewing stats — is reachable from `/manage` and
`/match`; Telegram is a convenience layer on top, never a requirement. Enable the [telegram](plugins/telegram/README.md) plugin if you
want meetups posted to a group chat automatically, with join/leave buttons, and admin
commands from Telegram.

## 2. Bootstrap a workspace

Pick an empty directory for this instance's config and data, then run:

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball --bootstrap
```

This creates, in the current directory:

```
config.toml     # your settings — edit this next
compose.yaml    # docker compose service definition
.env            # UID/GID/PORT/TAG used by compose.yaml
README.md       # a short pointer back to this guide
data/           # JSON data files (see docs/data-directory.md)
logs/           # application logs
```

`--bootstrap` refuses to run if any of `config.toml`, `compose.yaml`, or `.env` already
exist in the target directory, so it's safe to re-run — it won't overwrite your setup.

## 3. Configure `config.toml`

Every key can also be set with an environment variable, `PYBALL_<SECTION>_<KEY>`
(e.g. `PYBALL_CORE_LOCATION`, `PYBALL_ALERTS_TELEGRAM_BOT_TOKEN`) — useful for keeping secrets
out of `config.toml` or overriding a value per-deployment without editing the file.

### `[pyball.core]`

| Key | Description | Default |
|---|---|---|
| `location` | Default meetup location | *(required)* |
| `name` | Instance name shown in the UI | *(required)* |
| `default_week_day` | Default day (`monday`–`sunday`) for new meetups | `wednesday` |
| `default_hour` | Default start time (`HH:MM`) | `20:00` |
| `meetup_capacity` | Players a new meetup plays with; each meetup's capacity can then be changed from `/manage` | `10` |
| `display_date_format` | Date format used in messages, served to plugins by `GET /api/v1/settings` | `%Y-%m-%d %H:%M` |
| `team_colors` | Two or three color names: the first two are the classic-match teams, the third is only used for triangulars (auto-filled if you list just two) | `["blanco", "negro", "rojo"]` |
| `base_url` | Public URL used to build the `/match` link | *(required)* |
| `api_port` | HTTP server port | `8000` |
| `locale` | Locale used to sort player names, served to plugins by `GET /api/v1/settings` | `es_ES.UTF-8` |
| `data_dir` | Directory for JSON data files; a relative path starts from the folder holding `config.toml` | `data` |
| `match_token` | Access token for `/match` only (optional, see [Access tokens](#6-access-tokens)) | *(empty)* |
| `manage_token` | Access token for everything, including `/manage` (optional) | *(empty)* |
| `theme_color` | PWA theme/background color | `#0f172a` |
| `icons_dir` | Custom PWA icons directory (optional); a relative path starts from the folder holding `config.toml` | *(empty)* |

Available team colors: `blanco` `negro` `rojo` `naranja` `amarillo` `verde` `azul`
`morado` `marron`.

`deploy/deploy.sh` sends its own deploy notifications with the bot token, chat and
forum topic in the `DEPLOY_NOTIFY_TOKEN`, `DEPLOY_NOTIFY_CHAT_ID` and
`DEPLOY_NOTIFY_THREAD_ID` GitHub secrets — point them at the same chat and topic as
[`alerts.telegram`](#pyballalertstelegram--alerts). Without `DEPLOY_NOTIFY_TOKEN`, deploys send no
notifications.

### `[pyball.alerts.telegram]` — alerts

PyBall's own warnings and errors, a plugin that crashes or keeps restarting included, go
to this Telegram chat. The core sends them itself, so they need no plugin running. The
same alert is sent at most once every 10 minutes, and the next one says how many repeats
it left out, so a crash loop can't flood the chat. PyBall also posts there when it starts
and when it stops. Without the section, or with `chat_id = 0`, alerts are off and PyBall
says so in its startup log. Env overrides follow `PYBALL_ALERTS_TELEGRAM_<KEY>`.

| Key | Description | Required |
|---|---|---|
| `bot_token` | Token of the bot that sends the alerts; it may be the same bot as the telegram plugin's | When `chat_id` is set |
| `chat_id` | Chat that receives the alerts (negative for groups; `0` / omit to disable) | No |
| `message_thread_id` | Forum topic for the alerts (empty = none) | No |

### `[pyball.plugins.<name>]` — optional plugins

One table per plugin, named after it (see [Plugins](#8-plugins)). These tables have no env overrides.

| Key | Description | Required |
|---|---|---|
| `command` | Program and arguments that start the plugin, run from the workspace, e.g. `["./plugins/example-plugin", "--verbose"]` | **Yes** |
| `scopes` | What the plugin may do through the plugin API: any of `players:read`, `players:write`, `meetups:read` (includes the event stream), `meetups:write` | No (none) |

Any other key in the table is the plugin's own setting: each bundled plugin documents
its keys, e.g. [siesta](plugins/siesta/README.md#enable-it).

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

See [docs/workflow.md](workflow.md) for the full step-by-step flow.

## 6. Access tokens

`match_token` and `manage_token` protect the app when it's exposed
beyond your own private network (e.g. through a reverse proxy on the public internet) —
without them, `/manage` and `/match` are open to anyone who reaches the URL.
If both are left empty, no authentication is enforced at all (fine for a private
network you already trust). How you expose the app publicly (reverse proxy, VPN, tunnel,
etc.) is up to you — these tokens work the same regardless.

| Path | Required token |
|---|---|
| `/`, static assets, PWA manifests | None (always public) |
| `/match`, `GET /api/match/active`, `POST /api/match/finish` | `match_token` **or** `manage_token` |
| `/api/v1/*` (the plugin API) | `Authorization: Bearer` with a plugin's own token **or** `manage_token` — see [Plugins](#8-plugins) |
| `/manage` and everything else under `/api/*` | `manage_token` only |

Give the scoreboard-only `match_token` to a device that should only ever see `/match`
(e.g. a tablet mounted at the pitch), and the `manage_token` to admins. Visiting a URL with `?token=<value>` once validates it
and sets an `HttpOnly` cookie that lasts a year — no need to pass the token again after
that on the same device/browser.

## 7. Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version instead of always tracking `latest` by setting `TAG=4.13.0` in
`.env`.

## 8. Plugins

A plugin is an optional, long-running program that extends PyBall without touching its
code. Some come bundled in the PyBall image:
[telegram](plugins/telegram/README.md), the Telegram bot;
[siesta](plugins/siesta/README.md), the fair sit-out draw; and
[activity](plugins/activity/README.md), the activity feed. You can also add your own to
the workspace's `plugins/` folder. Either kind runs only once you declare it under
[`[pyball.plugins.<name>]`](#pyballpluginsname--optional-plugins).

See **[docs/plugins/README.md](plugins/README.md)** for the bundled plugins, how PyBall
runs a plugin, the plugin API and the event stream.

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
