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
import logging
import logging.handlers

from pyball.settings import LOGS_DIRECTORY_PATH

basic_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

stream_log = logging.StreamHandler()
stream_log.setLevel(logging.INFO)

full_log = logging.handlers.RotatingFileHandler(
    LOGS_DIRECTORY_PATH.joinpath("bot.log"),
    maxBytes=1024 * 1024,
    backupCount=5,
)
full_log.setFormatter(logging.Formatter(basic_fmt))
full_log.setLevel(logging.DEBUG)

pyball_log = logging.handlers.TimedRotatingFileHandler(
    LOGS_DIRECTORY_PATH.joinpath("pyball.log"),
    when="W2",
    backupCount=5,
    atTime=datetime.time(hour=23, minute=59),
)
pyball_log.addFilter(logging.Filter("pyball"))
pyball_log.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s:%(lineno)d(%(funcName)s) - %(levelname)s - %(message)s"
    )
)
pyball_log.setLevel(logging.DEBUG)

logging.basicConfig(
    format=basic_fmt,
    level=logging.DEBUG,
    handlers=(stream_log, full_log, pyball_log),
)

PYBALL_LOGGER = logging.getLogger(__name__)
