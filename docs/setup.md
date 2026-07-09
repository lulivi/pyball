# Setup Guide

🇬🇧 English | 🇪🇸 [Español](setup.es.md)

This guide covers installing, configuring, and running PyBall as an end user. If you
want to build PyBall from source or contribute to it, see the
[Development section of the main README](../README.md#development) instead.

## 1. Choose a topology

PyBall ships as two Docker images, built from the same codebase:

| Image | What it runs | Needs a Telegram bot? |
|---|---|---|
| `lulivi/pyball-web` | FastAPI only — `/manage` and `/match` web pages | No |
| `lulivi/pyball-telegram` | Telegram bot + FastAPI (same web pages) | Yes |

If your group doesn't use Telegram, or you'd rather manage everything from the browser,
use `pyball-web`: every feature — creating meetups, building teams (classic or
triangular), tracking a match, closing a triangular session, viewing stats — is
reachable from `/manage` and `/match`. Use `pyball-telegram` if you want meetups posted
to a group chat automatically, admin commands from Telegram, and reactions/notifications
in the chat.

## 2. Bootstrap a workspace

Pick an empty directory for this instance's config and data, then run:

```bash
mkdir pyball && cd pyball
docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd):/pyball" lulivi/pyball-web --bootstrap
# or:
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

### `[pyball.core]` — both topologies

| Key | Description | Default |
|---|---|---|
| `location` | Default meetup location | *(required)* |
| `name` | Instance name shown in the UI | *(required)* |
| `default_week_day` | Default day (`monday`–`sunday`) for new meetups | `wednesday` |
| `default_hour` | Default start time (`HH:MM`) | `20:00` |
| `display_date_format` | Date format used in messages | `%Y-%m-%d %H:%M` |
| `team_colors` | Three color names: the first two are the classic-match teams, the third is only used for triangulars | `["blanco", "negro", "rojo"]` |
| `base_url` | Public URL used to build the `/match` link | *(required)* |
| `api_port` | HTTP server port | `8000` |
| `locale` | Locale used to sort player names | `es_ES.UTF-8` |
| `data_dir` | Directory for JSON data files | `data` |
| `match_token` | Access token for `/match` only (optional, see [Access tokens](#6-access-tokens)) | *(empty)* |
| `manage_token` | Access token for everything, including `/manage` (optional) | *(empty)* |
| `theme_color` | PWA theme/background color | `#0f172a` |
| `icons_dir` | Custom PWA icons directory (optional) | *(empty)* |

Available team colors: `blanco` `negro` `rojo` `naranja` `amarillo` `verde` `azul`
`morado` `marron`.

### `[pyball.telegram]` and sub-sections — `pyball-telegram` only

These are ignored by `pyball-web` — see
[Telegram config is bot-only](data-directory.md#telegram-config-is-bot-only) for why.

| Key | Description |
|---|---|
| `telegram.bot_token` | Bot token from [@BotFather](https://t.me/BotFather) |
| `telegram.admins_ids` | Telegram user IDs allowed to run admin commands |
| `telegram.regulars.chat_id` | Main group chat ID (negative number for groups) |
| `telegram.regulars.meetups_thread_id` | Forum topic thread for callup messages (empty to disable) |
| `telegram.regulars.stats_thread_id` | Forum topic thread for post-match stats (empty to disable) |
| `telegram.substitutes.chat_id` | Substitutes group chat ID (negative number for groups) |
| `telegram.management.chat_id` | Operational log channel ID (`0` to disable) |

To find a chat ID: add the bot to the group, send any message, then check
`https://api.telegram.org/bot<TOKEN>/getUpdates` for the `chat.id` field.

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

`match_token` and `manage_token` protect the app when it's exposed outside your own
network (e.g. via [Tailscale Funnel](https://tailscale.com/kb/1223/funnel)) — without
them, `/manage` and `/match` are open to anyone who reaches the URL. If both are left
empty, no authentication is enforced at all (fine for a private network you already
trust).

| Path | Required token |
|---|---|
| `/`, static assets, PWA manifests | None (always public) |
| `/match`, `GET /api/match/active`, `POST /api/match/finish` | `match_token` **or** `manage_token` |
| `/manage` and everything else under `/api/*` | `manage_token` only |

Give the scoreboard-only `match_token` to a device that should only ever see `/match`
(e.g. a tablet mounted at the pitch), and the `manage_token` to admins. Visiting a URL
with `?token=<value>` once validates it and sets an `HttpOnly` cookie that lasts a year —
no need to pass the token again after that on the same device/browser.

## 7. Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version instead of always tracking `latest` by setting `TAG=4.13.0` in
`.env`.

## Next steps

- [docs/workflow.md](workflow.md) — the full meetup lifecycle: creating a meetup,
  building teams, the classic vs triangular formats, tracking a match, and stats.
- [docs/data-directory.md](data-directory.md) — what's inside `data/`, and the JSON
  format of each file.
