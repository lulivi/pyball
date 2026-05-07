# Copyright (c) 2022 Luis Liñán
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
"""Loging module."""

import datetime
import functools
import json
import logging
import logging.handlers
import urllib.request
from typing import Any, Callable, TypeVar, cast

from pyball.settings import LOGS_DIRECTORY_PATH, Settings


def config_logging(settings: Settings) -> None:
    """Configure log files."""
    LOGS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = []

    stream_log = logging.StreamHandler()
    stream_log.setLevel(logging.INFO)
    handlers.append(stream_log)
    handlers.append(
        logging.handlers.RotatingFileHandler(
            LOGS_DIRECTORY_PATH.joinpath("full.log"),
            maxBytes=1024 * 1024,
            backupCount=5,
        )
    )
    handlers.append(timed_rotating_file_handler("pyball.log", "pyball"))
    handlers.append(timed_rotating_file_handler("bot.log", "pyball.bot"))
    handlers.append(timed_rotating_file_handler("infrastructure.log", "pyball.infrastructure"))
    if settings.telegram.management.chat_id:
        handlers.append(telegram_log_handler(settings))

    logging.basicConfig(
        format="{asctime}|{levelname}|{name}:{lineno: 4d}| {message}",
        datefmt="%Y-%m-%dT%H:%M:%S",
        style="{",
        level=logging.DEBUG,
        handlers=handlers,
    )

    # Third-party loggers
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def timed_rotating_file_handler(
    file_name: str,
    filter_string: str,
) -> logging.handlers.TimedRotatingFileHandler:
    """Create a log file handler with filter.

    :param file_name: Name of the file inside the logs directory.
    :param filter_string: Log file.
    :returns: The newly created log handler.

    """
    log = logging.handlers.TimedRotatingFileHandler(
        LOGS_DIRECTORY_PATH.joinpath(file_name),
        when="W2",
        backupCount=5,
        atTime=datetime.time(hour=23, minute=59),
    )
    log.addFilter(logging.Filter(filter_string))
    return log


def telegram_log_handler(settings: Settings) -> logging.Handler:
    """Build a TelegramLogHandler for the management chat."""
    handler = TelegramLogHandler(settings.telegram.bot_token, settings.telegram.management.chat_id)
    handler.addFilter(_ManagementFilter())
    return handler


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
            text = (
                f"{emoji} {record.levelname}\n`{record.name}:{record.lineno}`\n```{message}\n```"
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


# Function type definition to preserve typing of the wrapped function
F = TypeVar("F", bound=Callable[..., Any])


def log_func(func: F) -> F:
    """Log the function ussage."""
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        """Wrap the function."""
        logger.debug(">>>>> Entering %s function", func.__name__)
        ret_val = func(*args, **kwargs)
        logger.debug("<<<<< Exiting %s function", func.__name__)
        return ret_val

    return cast(F, decorator)
