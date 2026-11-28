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

# Players a new meetup plays with; change it per meetup from /manage
# Override with PYBALL_CORE_MEETUP_CAPACITY
meetup_capacity = 10

# Override with PYBALL_CORE_DISPLAY_DATE_FORMAT
display_date_format = "%Y-%m-%d %H:%M"

# Colors for the teams: 2 or 3 names. The first two are the classic-match teams;
# a 3rd (only used for triangulars) is auto-filled when you list just 2.
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

# Relative to this file's folder, like icons_dir; logs/ and plugins/ live here too
# Override with PYBALL_CORE_DATA_DIR
data_dir = "data"

# Static tokens for public access (optional -- leave empty to disable auth)
# Override with PYBALL_CORE_MATCH_TOKEN
# match_token = ""

# Override with PYBALL_CORE_MANAGE_TOKEN
# manage_token = ""

# Override with PYBALL_CORE_THEME_COLOR
theme_color = "#0f172a"

# Override with PYBALL_CORE_ICONS_DIR
icons_dir = ""

[pyball.alerts.telegram]
# Core warnings and errors, plugin crashes included; no plugin needed.
# chat_id = 0 disables alerts. The bot token may be the one the telegram plugin uses.
# Point the deploy notification secrets (DEPLOY_NOTIFY_*) at this chat too.
# Override with PYBALL_ALERTS_TELEGRAM_BOT_TOKEN
bot_token = ""
# Override with PYBALL_ALERTS_TELEGRAM_CHAT_ID (negative for groups)
chat_id = 0
# Forum topic thread (empty string = no topic)
# Override with PYBALL_ALERTS_TELEGRAM_MESSAGE_THREAD_ID
message_thread_id = ""

# Plugins the core starts, supervises and stops (one table per plugin, no env overrides).
# A plugin is a long-running program, bundled (siesta, activity, telegram) or yours in plugins/;
# one that exits is started again. Bundled ones: docs/plugins/README.md
# Scopes: players:read  players:write  meetups:read  meetups:write
# [pyball.plugins.example]
# command = ["./plugins/example-plugin", "--verbose"]
# scopes = ["players:read", "meetups:read", "meetups:write"]
"""

_PYBALL_COMPOSE = """\
services:
  pyball:
    image: lulivi/pyball:${TAG:-latest}
    user: "${UID}:${GID}"
    ports:
      - "127.0.0.1:${PORT}:8000"
    volumes:
      - "./config.toml:/pyball/config.toml"
      - "./logs:/pyball/logs"
      - "./data:/pyball/data"
      - "./plugins:/pyball/plugins"
    restart: unless-stopped
"""

_DOCS_BASE_URL = "https://github.com/lulivi/pyball/blob/main/docs"

_PYBALL_README = f"""\
# PyBall

PyBall is a self-hosted football meetup manager with a web UI for tracking matches,
managing players, and recording results, and an optional Telegram bot, the bundled
`telegram` plugin.

## Quick Start

```bash
docker compose up -d
```

Edit `config.toml` first — see the full setup guide for configuration, access tokens
and how to use `/manage` and `/match`:

- [Setup Guide]({_DOCS_BASE_URL}/setup.md) / [Guía de instalación]({_DOCS_BASE_URL}/setup.es.md)
- [Application Workflow]({_DOCS_BASE_URL}/workflow.md) / \
[Flujo de la aplicación]({_DOCS_BASE_URL}/workflow.es.md)
- [Data Directory]({_DOCS_BASE_URL}/data-directory.md) / \
[Directorio de datos]({_DOCS_BASE_URL}/data-directory.es.md)

## Updating

```bash
docker compose pull
docker compose up -d
```

Pin a specific version in `.env`: `TAG=4.13.0`
"""


def init_workspace(config_path: Path) -> None:
    """Generate a deployment workspace and exit without starting the app.

    Args:
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

    print(f"Bootstrapping pyball workspace in {workspace} ...")

    for rel in ("data", "data/meetups", "logs", "plugins"):
        (workspace / rel).mkdir(parents=True, exist_ok=True)
        print(f"  Created  {rel}/")

    config_path.write_text(_CORE_CONFIG, encoding="utf-8")
    print("  Written  config.toml")

    compose_path.write_text(_PYBALL_COMPOSE, encoding="utf-8")
    print("  Written  compose.yaml")

    env_path.write_text(_env_template(), encoding="utf-8")
    print("  Written  .env")

    if readme_path.exists():
        print("  Skipped  README.md (already exists)")
    else:
        readme_path.write_text(_PYBALL_README, encoding="utf-8")
        print("  Written  README.md")

    print()
    print("Next steps:")
    print("  1. Edit config.toml with your settings")
    print("  2. Edit .env -- set PORT to the local port you want to expose")
    print("  3. docker compose up -d")


def _env_template() -> str:
    """Return the .env content with auto-detected UID and GID."""
    return f"UID={os.getuid()}\n" f"GID={os.getgid()}\n" "PORT=8000\n" "TAG=latest\n"
