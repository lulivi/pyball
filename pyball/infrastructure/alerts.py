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
"""Alerts: core warnings and errors sent to a Telegram chat, in every topology.

Alerts run in the core process and need no plugin, so they keep arriving while every plugin
is down, including one that keeps crashing.
"""

from __future__ import annotations

import atexit
import json
import logging
import logging.handlers
import queue
import time
import urllib.request

from pyball.settings import TelegramAlerts

logger = logging.getLogger(__name__)

REPEAT_WINDOW = 600.0
"""Seconds the same alert stays quiet after it is sent; repeats in between are counted."""


def config_alerts(alerts: TelegramAlerts | None) -> None:
    """Send alerts to ``alerts``' chat from a background thread, or warn that they are off.

    Records are queued on the logging call and sent by a listener thread, so a slow or
    unreachable Telegram never blocks the event loop. The queue drains at exit.
    """
    if alerts is None:
        logger.warning("pyball.alerts.telegram no está configurado: las alertas no se enviarán.")
        return
    records: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    queue_handler = logging.handlers.QueueHandler(records)
    queue_handler.addFilter(_AlertFilter())
    listener = logging.handlers.QueueListener(
        records,
        TelegramAlertHandler(alerts.bot_token, alerts.chat_id, alerts.message_thread_id),
    )
    listener.start()
    atexit.register(listener.stop)
    logging.getLogger().addHandler(queue_handler)


class TelegramAlertHandler(logging.Handler):
    """Logging handler that sends records to a Telegram chat via the Bot API.

    The same alert, one logging call for one plugin (its ``plugin`` extra), is sent at
    most once per ``REPEAT_WINDOW``; the next one sent says how many were left out, so a
    crash loop or an error inside a loop gives a bounded number of messages.
    """

    _formatter: logging.Formatter = logging.Formatter()
    _LEVEL_EMOJI: dict[int, str] = {
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "🔴",
        logging.CRITICAL: "💀",
    }

    def __init__(self, bot_token: str, chat_id: int, message_thread_id: int | None = None) -> None:
        """Initialize the handler with Telegram credentials and optional topic."""
        super().__init__()
        self._token = bot_token
        self._chat_id = chat_id
        self._message_thread_id = message_thread_id
        self._last_sent: dict[tuple[str, int, str | None], float] = {}
        self._suppressed: dict[tuple[str, int, str | None], int] = {}

    def emit(self, record: logging.LogRecord) -> None:
        """Send the record to the alert chat."""
        key = (record.name, record.lineno, getattr(record, "plugin", None))
        now = time.monotonic()
        last = self._last_sent.get(key)
        if last is not None and now - last < REPEAT_WINDOW:
            self._suppressed[key] = self._suppressed.get(key, 0) + 1
            return
        suppressed = self._suppressed.get(key, 0)
        try:
            emoji = self._LEVEL_EMOJI.get(record.levelno, "❓")
            message = record.getMessage()
            if record.exc_info:
                message += "\n" + self._formatter.formatException(record.exc_info)
            safe_message = message.replace("```", "'''")
            text = (
                f"{emoji} {record.levelname}\n`{record.name}:{record.lineno}`\n"
                f"```{safe_message}\n```"
            )
            if suppressed:
                text += f"\n\\(\\+{suppressed} alertas iguales omitidas\\)"
            payload_data: dict[str, object] = {
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "MarkdownV2",
            }
            if self._message_thread_id is not None:
                payload_data["message_thread_id"] = self._message_thread_id
            payload = json.dumps(payload_data).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0):
                pass
            self._last_sent[key] = now  # a failed send leaves the alert free to retry
            self._suppressed.pop(key, None)
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


class _AlertFilter(logging.Filter):
    """Passes pyball.* records at WARNING+ and records of any other logger at ERROR+."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True if the record is an alert."""
        if record.name.startswith("pyball."):
            return record.levelno >= logging.WARNING
        return record.levelno >= logging.ERROR
