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
"""Static page and manifest route registrar."""
from __future__ import annotations

from importlib.metadata import version as _package_version
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response

if TYPE_CHECKING:
    from pyball.application.container import Container


def register_static_routes(
    app: FastAPI, static_dir: Path, container: "Container", enable_web_signup: bool = False
) -> None:
    """Register the health-check, static-page, manifest, config, and SW routes."""

    @app.get("/")
    async def health():
        """Return a simple status response."""
        return {"status": "ok"}

    @app.get("/api/config")
    async def app_config():
        """Return topology capability flags for the shared /manage frontend."""
        return {"signup_enabled": enable_web_signup}

    @app.get("/match")
    async def match_page():
        """Serve the match tracker SPA."""
        content = (static_dir / "match.html").read_text()
        return HTMLResponse(content)

    @app.get("/manage")
    async def manage_page():
        """Serve the manage tracker SPA."""
        content = (static_dir / "manage.html").read_text()
        return HTMLResponse(content)

    @app.get("/sw.js")
    async def service_worker():
        """Serve the service worker with the package version baked into the cache name."""
        content = (static_dir / "sw.js").read_text()
        content = content.replace("__VERSION__", _package_version("pyball"))
        return Response(content, media_type="application/javascript")

    _icons = [
        {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ]

    @app.get("/manifest-match.json")
    async def manifest_match():
        """Return the dynamic PWA manifest for the match page."""
        color = container.theme_color
        return {
            "name": f"PyBall – Partido {container.name}",
            "short_name": f"Partido {container.name}",
            "id": "/match",
            "scope": "/match",
            "start_url": "/match",
            "display": "standalone",
            "background_color": color,
            "theme_color": color,
            "icons": _icons,
        }

    @app.get("/manifest-manage.json")
    async def manifest_manage():
        """Return the dynamic PWA manifest for the manage page."""
        color = container.theme_color
        return {
            "name": f"PyBall – Gestión {container.name}",
            "short_name": f"Gestión {container.name}",
            "id": "/manage",
            "scope": "/manage",
            "start_url": "/manage",
            "display": "standalone",
            "background_color": color,
            "theme_color": color,
            "icons": _icons,
        }
