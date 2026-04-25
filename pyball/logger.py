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
import logging
import logging.handlers
from typing import Any, Callable, TypeVar, cast

from pyball.settings import LOGS_DIRECTORY_PATH


def config_logging() -> None:
    """Configure log files."""
    LOGS_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)
    stream_log = logging.StreamHandler()
    stream_log.setLevel(logging.INFO)

    full_log = logging.handlers.RotatingFileHandler(
        LOGS_DIRECTORY_PATH.joinpath("full.log"),
        maxBytes=1024 * 1024,
        backupCount=5,
    )

    pyball_log = timed_rotating_file_handler("pyball.log", "pyball")
    bot_log = timed_rotating_file_handler("bot.log", "pyball.bot")
    infra_log = timed_rotating_file_handler("infrastructure.log", "pyball.infrastructure")

    logging.basicConfig(
        format="{asctime}|{levelname}|{name}:{lineno: 4d}| {message}",
        datefmt="%Y-%m-%dT%H:%M:%S",
        style="{",
        level=logging.DEBUG,
        handlers=(
            stream_log,
            full_log,
            pyball_log,
            bot_log,
            infra_log,
        ),
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
