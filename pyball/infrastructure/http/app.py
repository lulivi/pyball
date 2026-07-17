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
"""FastAPI application factory."""
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pyball.infrastructure.http.auth import TokenAuthMiddleware
from pyball.infrastructure.http.routes import (
    register_match_routes,
    register_meetup_routes,
    register_player_routes,
    register_signup_routes,
    register_static_routes,
)

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.application.notifier import MatchNotifier

_DEFAULT_STATIC_DIR = Path(__file__).parent / "static"
_DEFAULT_SIGNUP_STATIC_DIR = Path(__file__).parent / "static_signup"


def create_app(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    container: "Container",
    notifier: "MatchNotifier",
    static_dir: Path = _DEFAULT_STATIC_DIR,
    signup_static_dir: Path = _DEFAULT_SIGNUP_STATIC_DIR,
    match_token: str = "",
    manage_token: str = "",
    signup_token: str = "",
    enable_web_signup: bool = False,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="PyBall API")

    if match_token or manage_token or signup_token:
        app.add_middleware(
            TokenAuthMiddleware,
            match_token=match_token,
            manage_token=manage_token,
            signup_token=signup_token,
        )

    register_static_routes(app, static_dir, container, enable_web_signup=enable_web_signup)
    register_match_routes(app, container, notifier)
    register_player_routes(app, container, enable_web_signup=enable_web_signup)
    register_meetup_routes(app, container, notifier)
    if enable_web_signup:
        register_signup_routes(app, container, signup_token, static_dir=signup_static_dir)

    icons_dir = Path(container.icons_dir) if container.icons_dir else None
    if icons_dir and icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")

    if enable_web_signup and signup_static_dir.exists():
        app.mount("/signup-static", StaticFiles(directory=signup_static_dir), name="signup-static")

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


class _Server(uvicorn.Server):
    """Uvicorn server that defers signal handling to the caller."""

    def install_signal_handlers(self) -> None:
        """No-op: signals are managed by the entrypoint."""
