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
"""Runs every declared plugin as a child process: starts, restarts and stops them."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path

from pyball.infrastructure.plugins.auth import PluginCredentials
from pyball.settings import PluginConfig

logger = logging.getLogger(__name__)


class PluginSupervisor:  # pylint: disable=too-many-instance-attributes
    """Keeps each plugin running; a crash is logged and restarted, never fatal to the core.

    A plugin gets PYBALL_API_URL, PYBALL_API_TOKEN and PYBALL_PLUGIN_NAME in its
    environment and runs in its own process group from ``cwd``. Its output goes to the
    log, one record per line. Restarts wait ``min_backoff``, doubling up to
    ``max_backoff``; a run that lasted ``stable_after`` seconds resets the wait.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        plugins: list[PluginConfig],
        credentials: PluginCredentials,
        api_url: str,
        cwd: Path,
        *,
        min_backoff: float = 1.0,
        max_backoff: float = 60.0,
        stable_after: float = 60.0,
        stop_timeout: float = 10.0,
    ) -> None:
        """Prepare to run ``plugins``; nothing starts until start()."""
        self._plugins = plugins
        self._credentials = credentials
        self._api_url = api_url
        self._cwd = cwd
        self._min_backoff = min_backoff
        self._max_backoff = max_backoff
        self._stable_after = stable_after
        self._stop_timeout = stop_timeout
        self._stopping = asyncio.Event()
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._tasks: list[asyncio.Task[None]] = []

    def start(self) -> None:
        """Start every plugin."""
        self._tasks = [asyncio.create_task(self._keep_running(p)) for p in self._plugins]

    async def stop(self) -> None:
        """Stop restarting, send SIGTERM to every plugin, and SIGKILL what outlives the wait."""
        self._stopping.set()
        running = [p for p in self._processes.values() if p.returncode is None]
        for process in running:
            _signal_group(process, signal.SIGTERM)
        if running:
            _, late = await asyncio.wait(
                [asyncio.create_task(p.wait()) for p in running], timeout=self._stop_timeout
            )
            if late:
                for process in running:
                    if process.returncode is None:
                        _signal_group(process, signal.SIGKILL)
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _keep_running(self, plugin: PluginConfig) -> None:
        backoff = self._min_backoff
        loop = asyncio.get_running_loop()
        while not self._stopping.is_set():
            started = loop.time()
            try:
                await self._run_once(plugin)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Plugin %s failed", plugin.name, extra={"plugin": plugin.name})
            if self._stopping.is_set():
                return
            if loop.time() - started >= self._stable_after:
                backoff = self._min_backoff
            logger.warning(
                "Plugin %s stopped; restarting in %.0fs",
                plugin.name,
                backoff,
                extra={"plugin": plugin.name},
            )
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, self._max_backoff)

    async def _run_once(self, plugin: PluginConfig) -> None:
        env = {
            **os.environ,
            "PYBALL_API_URL": self._api_url,
            "PYBALL_API_TOKEN": self._credentials.token_for(plugin.name),
            "PYBALL_PLUGIN_NAME": plugin.name,
        }
        try:
            process = await asyncio.create_subprocess_exec(
                *plugin.command,
                cwd=self._cwd,
                env=env,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            logger.error(
                "Plugin %s could not start: %s", plugin.name, exc, extra={"plugin": plugin.name}
            )
            return
        self._processes[plugin.name] = process
        if self._stopping.is_set():  # stop() began while it was spawning
            _signal_group(process, signal.SIGKILL)
        logger.info("Plugin %s started (pid %d)", plugin.name, process.pid)
        plugin_logger = logging.getLogger(f"pyball.plugins.{plugin.name}")
        assert process.stdout is not None
        try:
            async for line in process.stdout:
                plugin_logger.info("%s", line.decode(errors="replace").rstrip())
        finally:
            if process.returncode is None and not self._stopping.is_set():
                _signal_group(process, signal.SIGKILL)  # its output stopped being readable
        code = await process.wait()
        logger.info("Plugin %s exited with code %d", plugin.name, code)


def _signal_group(process: asyncio.subprocess.Process, sig: signal.Signals) -> None:
    """Signal the plugin's whole process group, so its own children stop with it."""
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass
