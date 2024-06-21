#!/usr/bin/env python3
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
"""Bot main file."""

import logging

from argparse import ArgumentParser

from telegram.ext import Application

from pyball import __version__
from pyball.greenfield.utils.bot.commands.entrypoint import (
    build_application as build_greenfield_application,
)
from pyball.legacy.bot import build_application as build_legacy_application
from pyball.legacy.db.write_events import *  # pylint: disable=wildcard-import,unused-wildcard-import

logger = logging.getLogger(__name__)


def log_startup_info() -> None:
    """Log some important information in the startup."""
    asterisk_line = "*" * 79
    booting_up_str = "Booting up!!"
    pyball_version_str = f"Running Pyball v{__version__}"
    logger.warning(asterisk_line)
    logger.warning(f"*{booting_up_str:^77}*")
    logger.warning(f"*{pyball_version_str:^77}*")
    logger.warning(asterisk_line)


def main() -> None:
    """Start the bot."""
    parser = ArgumentParser(prog="pyball", description="Organise call-ups for your club!")
    parser.add_argument("-v", "--version", action="version", version=f"Pyball {__version__}")
    parser.add_argument("-g", "--greenfield", action="store_true", help="Use the new way")
    args = parser.parse_args()

    log_startup_info()

    application: Application
    if args.greenfield:
        logger.info("Using greenfield application builder")
        application = build_greenfield_application()
    else:
        logger.info("Using legacy application builder")
        application = build_legacy_application()

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
