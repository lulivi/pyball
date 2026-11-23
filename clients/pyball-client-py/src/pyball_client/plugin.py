"""How PyBall runs a plugin: the environment it sets, the plugin's own table in
``config.toml`` and the ``data/plugins/<name>/`` folder where the plugin keeps its state.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1"
"""Where the plugin API is when PYBALL_API_URL is not set, e.g. a command run by hand."""


class PluginError(Exception):
    """The plugin cannot start: its environment or configuration is wrong."""


def env(var: str) -> str | None:
    """Return an environment variable, None when unset or empty."""
    return os.environ.get(var) or None


def api_url() -> str:
    """Return PYBALL_API_URL without its trailing ``/``, or DEFAULT_API_URL."""
    return (env("PYBALL_API_URL") or DEFAULT_API_URL).rstrip("/")


def api_token() -> str:
    """Return PYBALL_API_TOKEN, which PyBall sets; by hand, the manage token."""
    token = env("PYBALL_API_TOKEN")
    if token is None:
        raise PluginError(
            "PYBALL_API_TOKEN is not set: PyBall sets it for the plugin; "
            "by hand, pass the manage token"
        )
    return token


def table(config_path: Path, name: str) -> dict[str, Any]:
    """Return the plugin's ``[pyball.plugins.<name>]`` table, empty if there is none."""
    try:
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PluginError(f"reading PyBall config {config_path}: {exc}") from exc
    found = doc.get("pyball", {}).get("plugins", {}).get(name, {})
    return found if isinstance(found, dict) else {}


def data_dir(name: str) -> Path:
    """Return the plugin's own folder, ``data/plugins/<name>/``, relative to the workspace."""
    return Path("data/plugins") / name


def load_event_id(path: Path) -> int | None:
    """Return the id of the last event the plugin handled, or None before the first one."""
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise PluginError(f"parsing {path}: {exc}") from exc


def save_event_id(path: Path, event_id: int) -> None:
    """Remember ``event_id`` as the last event handled."""
    write_atomic(path, f"{event_id}\n")


def write_atomic(path: Path, contents: str) -> None:
    """Write through a temp file and a rename, so a crash never leaves half a file.

    The temp name carries the process id: the plugin and a command run by hand may write
    at once.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(contents, encoding="utf-8")
    tmp.replace(path)
