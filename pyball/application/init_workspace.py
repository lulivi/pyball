# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Workspace initialisation for first-time deployment setup."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_CORE_CONFIG = """\
# PyBall Configuration
# Edit the values below, then run: docker compose up -d
# Any value can be overridden with environment variables using PYBALL_<SECTION>_<KEY>

[pyball.core]
# Override with PYBALL_CORE_LOCATION
location = "Parque Central"

# Override with PYBALL_CORE_NAME
name = "PyBall"

# Override with PYBALL_CORE_DEFAULT_WEEK_DAY (monday-sunday)
default_week_day = "wednesday"

# Override with PYBALL_CORE_DEFAULT_HOUR (HH:MM)
default_hour = "20:00"

# Override with PYBALL_CORE_DISPLAY_DATE_FORMAT
display_date_format = "%Y-%m-%d %H:%M"

# Colors for the teams (2 for classic matches, a 3rd for triangulars)
# Override with PYBALL_CORE_TEAM_COLORS (comma-separated, e.g. "amarillo,negro,rojo")
# Available: blanco  negro  rojo  naranja  amarillo  verde  azul  morado  marron
team_colors = ["blanco", "negro", "rojo"]

# The path prefix (derived from name) is appended automatically: base_url/name-slug/match
# Override with PYBALL_CORE_BASE_URL
base_url = "http://pyball:8000"

# Override with PYBALL_CORE_API_PORT
api_port = 8000

# Override with PYBALL_CORE_LOCALE
locale = "es_ES.UTF-8"

# Override with PYBALL_CORE_DATA_DIR
data_dir = "data"

# Static tokens for Tailscale Funnel access (optional -- leave empty to disable auth)
# Override with PYBALL_CORE_MATCH_TOKEN
# match_token = ""

# Override with PYBALL_CORE_MANAGE_TOKEN
# manage_token = ""

# Override with PYBALL_CORE_THEME_COLOR
theme_color = "#0f172a"

# Override with PYBALL_CORE_ICONS_DIR
icons_dir = ""
"""

_TG_CONFIG_EXTRA = """
[pyball.telegram]
# Override with PYBALL_TELEGRAM_BOT_TOKEN
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# Override with PYBALL_TELEGRAM_ADMINS_IDS (comma-separated)
admins_ids = [123456789, 987654321]

[pyball.telegram.regulars]
# Override with PYBALL_TELEGRAM_REGULARS_CHAT_ID (negative number for groups)
chat_id = -1000000000000

# Forum topic thread for meetup callup messages (empty string to disable)
# Override with PYBALL_TELEGRAM_REGULARS_MEETUPS_THREAD_ID
meetups_thread_id = ""

# Forum topic thread where post-match statistics are posted (empty string to disable)
# Override with PYBALL_TELEGRAM_REGULARS_STATS_THREAD_ID
stats_thread_id = ""

[pyball.telegram.substitutes]
# Override with PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID (negative number for groups)
chat_id = -1000000000001

[pyball.telegram.management]
# Management channel ID for operational log messages (0 to disable)
# Override with PYBALL_TELEGRAM_MANAGEMENT_CHAT_ID
chat_id = 0
"""

_WEB_COMPOSE = """\
services:
  web:
    image: lulivi/pyball-web:${TAG:-latest}
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
    restart: unless-stopped
"""

_TG_COMPOSE = """\
services:
  bot:
    image: lulivi/pyball-telegram:${TAG:-latest}
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
    restart: unless-stopped
"""

_WEB_README = """\
# PyBall

PyBall is a self-hosted football meetup manager with a web UI for tracking matches,
managing players, and recording results.

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

### Local (without Docker)

```bash
uv run pyball-web
```

## Configuration

Edit `config.toml` before starting. All values can also be set via environment
variables using the `PYBALL_<SECTION>_<KEY>` pattern.

| Key | Description | Default | Env var |
|-----|-------------|---------|---------|
| `core.location` | Default meetup location | — | `PYBALL_CORE_LOCATION` |
| `core.name` | Instance name shown in the UI | — | `PYBALL_CORE_NAME` |
| `core.default_week_day` | Default day (`monday`-`sunday`) | \
`wednesday` | `PYBALL_CORE_DEFAULT_WEEK_DAY` |
| `core.default_hour` | Default start time (`HH:MM`) | `20:00` | `PYBALL_CORE_DEFAULT_HOUR` |
| `core.display_date_format` | Date format in messages | \
`%Y-%m-%d %H:%M` | `PYBALL_CORE_DISPLAY_DATE_FORMAT` |
| `core.team_colors` | Three team colors: 2 for classic matches, a 3rd for \
triangulars (see below) | `["blanco","negro","rojo"]` | `PYBALL_CORE_TEAM_COLORS` |
| `core.base_url` | Public URL for match links | — | `PYBALL_CORE_BASE_URL` |
| `core.api_port` | HTTP server port | `8000` | `PYBALL_CORE_API_PORT` |
| `core.locale` | Locale for player name sorting | `es_ES.UTF-8` | `PYBALL_CORE_LOCALE` |
| `core.data_dir` | Directory for JSON data files | `data` | `PYBALL_CORE_DATA_DIR` |
| `core.match_token` | Token for match page auth (optional) | — | `PYBALL_CORE_MATCH_TOKEN` |
| `core.manage_token` | Token for manage page auth (optional) | — | `PYBALL_CORE_MANAGE_TOKEN` |
| `core.theme_color` | PWA theme/background color (optional) | \
`#0f172a` | `PYBALL_CORE_THEME_COLOR` |
| `core.icons_dir` | Custom icons directory (optional) | — | `PYBALL_CORE_ICONS_DIR` |

Available team colors: `blanco` `negro` `rojo` `naranja` `amarillo` `verde` \
`azul` `morado` `marron`

## Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version in `.env`: `TAG=4.13.0`
"""

_TG_README = """\
# PyBall

PyBall is a self-hosted football meetup manager with a Telegram bot and web UI for
tracking matches, managing players, and recording results.

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

### Local (without Docker)

```bash
uv run pyball-tg
```

## Configuration

Edit `config.toml` before starting. All values can also be set via environment
variables using the `PYBALL_<SECTION>_<KEY>` pattern.

### Core

| Key | Description | Default | Env var |
|-----|-------------|---------|---------|
| `core.location` | Default meetup location | — | `PYBALL_CORE_LOCATION` |
| `core.name` | Instance name shown in the UI | — | `PYBALL_CORE_NAME` |
| `core.default_week_day` | Default day (`monday`-`sunday`) | \
`wednesday` | `PYBALL_CORE_DEFAULT_WEEK_DAY` |
| `core.default_hour` | Default start time (`HH:MM`) | `20:00` | `PYBALL_CORE_DEFAULT_HOUR` |
| `core.display_date_format` | Date format in messages | \
`%Y-%m-%d %H:%M` | `PYBALL_CORE_DISPLAY_DATE_FORMAT` |
| `core.team_colors` | Three team colors: 2 for classic matches, a 3rd for \
triangulars (see below) | `["blanco","negro","rojo"]` | `PYBALL_CORE_TEAM_COLORS` |
| `core.base_url` | Public URL for match links | — | `PYBALL_CORE_BASE_URL` |
| `core.api_port` | HTTP server port | `8000` | `PYBALL_CORE_API_PORT` |
| `core.locale` | Locale for player name sorting | `es_ES.UTF-8` | `PYBALL_CORE_LOCALE` |
| `core.data_dir` | Directory for JSON data files | `data` | `PYBALL_CORE_DATA_DIR` |
| `core.match_token` | Token for match page auth (optional) | — | `PYBALL_CORE_MATCH_TOKEN` |
| `core.manage_token` | Token for manage page auth (optional) | — | `PYBALL_CORE_MANAGE_TOKEN` |
| `core.theme_color` | PWA theme/background color (optional) | \
`#0f172a` | `PYBALL_CORE_THEME_COLOR` |
| `core.icons_dir` | Custom icons directory (optional) | — | `PYBALL_CORE_ICONS_DIR` |

Available team colors: `blanco` `negro` `rojo` `naranja` `amarillo` `verde` \
`azul` `morado` `marron`

### Telegram

| Key | Description | Env var |
|-----|-------------|---------|
| `telegram.bot_token` | Telegram bot token from @BotFather | `PYBALL_TELEGRAM_BOT_TOKEN` |
| `telegram.admins_ids` | List of authorized Telegram user IDs | `PYBALL_TELEGRAM_ADMINS_IDS` |
| `telegram.regulars.chat_id` | Main group chat ID (negative) | \
`PYBALL_TELEGRAM_REGULARS_CHAT_ID` |
| `telegram.regulars.meetups_thread_id` | Forum topic for callup messages | \
`PYBALL_TELEGRAM_REGULARS_MEETUPS_THREAD_ID` |
| `telegram.regulars.stats_thread_id` | Forum topic for stats | \
`PYBALL_TELEGRAM_REGULARS_STATS_THREAD_ID` |
| `telegram.substitutes.chat_id` | Substitutes group chat ID (negative) | \
`PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID` |
| `telegram.management.chat_id` | Operational log channel ID (0 to disable) | \
`PYBALL_TELEGRAM_MANAGEMENT_CHAT_ID` |

## Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version in `.env`: `TAG=4.13.0`
"""


def init_workspace(topology: str, config_path: Path) -> None:
    """Generate a deployment workspace and exit without starting the app.

    Args:
        topology: "web" or "tg" — controls which config/compose/README template is used.
        config_path: Path where config.toml will be written; all other files go in
            the same directory.
    """
    workspace = config_path.parent.resolve()
    compose_path = workspace / "compose.yaml"
    env_path = workspace / ".env"
    readme_path = workspace / "README.md"

    errors = []
    if config_path.exists():
        errors.append(f"config.toml already exists in {workspace}")
    if compose_path.exists():
        errors.append(f"compose.yaml already exists in {workspace}")
    if env_path.exists():
        errors.append(f".env already exists in {workspace}")
    if errors:
        for msg in errors:
            print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

    print(f"Bootstrapping pyball-{topology} workspace in {workspace} ...")

    for rel in ("data", "data/meetups", "logs"):
        (workspace / rel).mkdir(parents=True, exist_ok=True)
        print(f"  Created  {rel}/")

    config_path.write_text(_config_template(topology), encoding="utf-8")
    print("  Written  config.toml")

    compose_path.write_text(_compose_template(topology), encoding="utf-8")
    print("  Written  compose.yaml")

    env_path.write_text(_env_template(), encoding="utf-8")
    print("  Written  .env")

    if readme_path.exists():
        print("  Skipped  README.md (already exists)")
    else:
        readme_path.write_text(_readme_template(topology), encoding="utf-8")
        print("  Written  README.md")

    print()
    print("Next steps:")
    print("  1. Edit config.toml with your settings")
    print("  2. Edit .env -- set PORT to the local port you want to expose")
    print("  3. docker compose up -d")


def _config_template(topology: str) -> str:
    """Return the config.toml content for the given topology."""
    if topology == "tg":
        return _CORE_CONFIG + _TG_CONFIG_EXTRA
    return _CORE_CONFIG


def _compose_template(topology: str) -> str:
    """Return the compose.yaml content for the given topology."""
    if topology == "tg":
        return _TG_COMPOSE
    return _WEB_COMPOSE


def _env_template() -> str:
    """Return the .env content with auto-detected UID and GID."""
    return f"UID={os.getuid()}\n" f"GID={os.getgid()}\n" "PORT=8000\n" "TAG=latest\n"


def _readme_template(topology: str) -> str:
    """Return the README.md content for the given topology."""
    if topology == "tg":
        return _TG_README
    return _WEB_README
