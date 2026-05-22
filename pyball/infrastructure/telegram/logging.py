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
"""Telegram-specific logging handler and setup."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyball.infrastructure.telegram.settings import TelegramSettings


def config_telegram_logging(tg: TelegramSettings) -> None:
    """Add a TelegramLogHandler to the root logger if management.chat_id is set."""
    if tg.management.chat_id:
        handler = TelegramLogHandler(tg.bot_token, tg.management.chat_id)
        handler.addFilter(_ManagementFilter())
        logging.getLogger().addHandler(handler)


class TelegramLogHandler(logging.Handler):
    """Logging handler that sends records to a Telegram chat via the Bot API."""

    _formatter: logging.Formatter = logging.Formatter()
    _LEVEL_EMOJI: dict[int, str] = {
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "🔴",
        logging.CRITICAL: "💀",
    }

    def __init__(self, bot_token: str, chat_id: int) -> None:
        """Initialize the handler with Telegram credentials."""
        super().__init__()
        self._token = bot_token
        self._chat_id = chat_id

    def emit(self, record: logging.LogRecord) -> None:
        """Send the formatted log record to the Telegram management channel."""
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
            payload = json.dumps(
                {"chat_id": self._chat_id, "text": text, "parse_mode": "MarkdownV2"}
            ).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0):
                pass
        except Exception:  # pylint: disable=broad-except
            self.handleError(record)


class _ManagementFilter(logging.Filter):
    """Passes pyball.* records at INFO+ and telegram records at ERROR+."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True if the record should be forwarded to the management channel."""
        if record.name.startswith("pyball.") and record.levelno >= logging.INFO:
            return True
        if (
            record.name == "telegram" or record.name.startswith("telegram.")
        ) and record.levelno >= logging.ERROR:
            return True
        return False
