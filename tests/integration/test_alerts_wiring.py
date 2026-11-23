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

"""PyBall sends core errors to the alert chat with no plugins."""

import asyncio
import json
import logging
import os
import signal
import socket
from unittest.mock import patch

import pytest

from pyball.cmd.run_pyball import _main_async


async def _until(condition, timeout: float = 10.0) -> None:
    async def poll():
        while not condition():
            await asyncio.sleep(0.05)

    await asyncio.wait_for(poll(), timeout)


def _serving(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


@pytest.mark.asyncio
async def test_pyball_sends_server_errors_to_the_alert_chat(tmp_path):
    """An error logged by the HTTP server, after it configured logging, reaches the chat."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = tmp_path / "config.toml"
    config.write_text(
        '[pyball.core]\nlocation = "Campo"\nname = "Test"\ndefault_week_day = "monday"\n'
        'default_hour = "20:00"\nbase_url = "http://localhost"\n'
        'team_colors = ["blanco", "negro"]\n'
        'locale = "C.UTF-8"\ndisplay_date_format = "%Y-%m-%d"\ndata_dir = "data"\n'
        f"api_port = {port}\n"
        '\n[pyball.alerts.telegram]\nbot_token = "tok"\nchat_id = -100111\n'
    )
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        with patch("pyball.infrastructure.alerts.atexit.register") as register, patch(
            "pyball.infrastructure.alerts.urllib.request.urlopen"
        ) as urlopen:
            task = asyncio.create_task(_main_async(config))
            await _until(lambda: _serving(port) or task.done())
            logging.getLogger("uvicorn.error").error("Exception in ASGI application")
            os.kill(os.getpid(), signal.SIGTERM)
            await asyncio.wait_for(task, 10)
            for call in reversed(register.call_args_list):  # atexit order: last first
                func, *args = call.args
                func(*args)
        texts = [json.loads(c.args[0].data)["text"] for c in urlopen.call_args_list]
        assert any("Exception in ASGI application" in t for t in texts)
        assert "arrancado" in texts[0]
        assert "PyBall detenido." in texts[-1]
    finally:
        for handler in root.handlers[:]:
            if handler not in before:
                root.removeHandler(handler)
