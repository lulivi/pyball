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

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response


def register_static_routes(app: FastAPI, static_dir: Path, name: str) -> None:
    """Register the health-check, static-page, manifest, and SW routes."""

    @app.get("/")
    async def health():
        """Return a simple status response."""
        return {"status": "ok"}

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
        return {
            "name": f"PyBall – Partido {name}",
            "short_name": f"Partido {name}",
            "id": "/match",
            "scope": "/match",
            "start_url": "/match",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "icons": _icons,
        }

    @app.get("/manifest-manage.json")
    async def manifest_manage():
        """Return the dynamic PWA manifest for the manage page."""
        return {
            "name": f"PyBall – Gestión {name}",
            "short_name": f"Gestión {name}",
            "id": "/manage",
            "scope": "/manage",
            "start_url": "/manage",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "icons": _icons,
        }
