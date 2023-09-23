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

from pyball import __version__
from pyball.bot import build_application
from pyball.db.write_events import *  # pylint: disable=wildcard-import,unused-wildcard-import

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    parser = ArgumentParser(prog="pyball", description="Organise call-ups for your club!")
    parser.add_argument("-v", "--version", action="version", version=f"Pyball {__version__}")
    parser.parse_args()

    logger.warning("**********************************************************")
    logger.warning("*********************** Booting up!! *********************")
    logger.warning("**********************************************************")

    # Create the pickle persistence
    application = build_application()

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
