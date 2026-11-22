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
"""Logging module."""

import datetime
import functools
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Callable, TypeVar, cast


def config_logging(logs_dir: Path) -> None:
    """Configure stream output and the log files in ``logs_dir``."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = []

    stream_log = logging.StreamHandler()
    stream_log.setLevel(logging.INFO)
    handlers.append(stream_log)
    handlers.append(
        logging.handlers.RotatingFileHandler(
            logs_dir / "full.log",
            maxBytes=1024 * 1024,
            backupCount=5,
        )
    )
    handlers.append(timed_rotating_file_handler(logs_dir / "pyball.log", "pyball"))
    handlers.append(timed_rotating_file_handler(logs_dir / "bot.log", "pyball.bot"))
    handlers.append(
        timed_rotating_file_handler(logs_dir / "infrastructure.log", "pyball.infrastructure")
    )

    logging.basicConfig(
        format="{asctime}|{levelname}|{name}:{lineno: 4d}| {message}",
        datefmt="%Y-%m-%dT%H:%M:%S",
        style="{",
        level=logging.DEBUG,
        handlers=handlers,
    )

    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def timed_rotating_file_handler(
    file_path: Path,
    filter_string: str,
) -> logging.handlers.TimedRotatingFileHandler:
    """Create a log file handler with filter.

    :param file_path: The log file.
    :param filter_string: Log filter prefix.
    :returns: The newly created log handler.
    """
    log = logging.handlers.TimedRotatingFileHandler(
        file_path,
        when="W2",
        backupCount=5,
        atTime=datetime.time(hour=23, minute=59),
    )
    log.addFilter(logging.Filter(filter_string))
    return log


F = TypeVar("F", bound=Callable[..., Any])


def log_func(func: F) -> F:
    """Log the function usage."""
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        """Wrap the function."""
        logger.debug(">>>>> Entering %s function", func.__name__)
        ret_val = func(*args, **kwargs)
        logger.debug("<<<<< Exiting %s function", func.__name__)
        return ret_val

    return cast(F, decorator)
