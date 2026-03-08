#!/usr/bin/env python3
# Copyright (c) 2023 Luis Liñán
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

"""Bot main file."""

import argparse
import asyncio
import locale
import logging

from typing import cast

from telegram.ext import Application

from pyballbot import __version__
from pyballbot.commands.entrypoint import build_application
from pyballbot.logger import configure_logging
from pyballbot.settings import APP_VERBOSITY, LOCALE
from pyballbot.event_bus import PyBallBotEventBus

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    args = parse_arguments()
    configure_logging(stream_level=args.verbosity)
    log_startup_info()

    # Set locale for sorting player names
    locale.setlocale(locale.LC_ALL, LOCALE)

    logger.info("Starting event bus listener")
    PyBallBotEventBus.start_listener()

    logger.info("Starting bot application")
    application: Application
    application = build_application()
    application.run_polling()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbosity",
        default=APP_VERBOSITY,
    )
    args = parser.parse_args()

    logging_levels = list(logging._nameToLevel)
    args.verbosity = cast(str, args.verbosity).upper()
    if args.verbosity not in logging_levels:
        parser.error(f"The argument --verbosity must be a valid logging level: {logging_levels}.")

    return args


def log_startup_info() -> None:
    """Log some important information in the startup."""
    asterisk_line = "*" * 79
    booting_up_str = "Booting up!!"
    pyball_version_str = f"Running Pyball v{__version__}"
    logger.warning(asterisk_line)
    logger.warning(f"*{booting_up_str:^77}*")
    logger.warning(f"*{pyball_version_str:^77}*")
    logger.warning(asterisk_line)

async def start_event_bus_listener():
    


if __name__ == "__main__":
    main()
