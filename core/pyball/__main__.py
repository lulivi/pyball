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
"""Core entrypoint."""

import argparse
import logging
import os

from typing import cast

import uvicorn

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from pyball import __version__
from pyball.logger import configure_logging, log_func
from pyball.meetup.infrastructure import api as meetup_api
from pyball.player.infrastructure import api as player_api
from pyball.settings import APP_VERBOSITY
from pyball.utils.api_exceptions import BaseApiException

logger = logging.getLogger(__name__)

app = FastAPI(title="Pyball", docs_url="/", version=__version__)

app.include_router(player_api.router, tags=["player"])
app.include_router(meetup_api.router, tags=["meetup"])


@app.exception_handler(BaseApiException)
async def unicorn_exception_handler(_: Request, exception: BaseApiException):
    logger.error(f"Sending exception: {exception.__class__.__name__}: {exception}")
    response = Response(status_code=exception.status)

    if exception.message:
        response = JSONResponse(
            content={"error": {"message": exception.message, "item": exception.item}}
        )

    return response


@log_func
@app.get("/status")
def status():
    return {"status": "OK"}


def main():
    """Launched with `poetry run start` at root level"""
    args = parse_arguments()
    configure_logging(stream_level=args.verbosity)

    logger.info("Starting application")
    try:
        uvicorn.run(
            "pyball.__main__:app", host="0.0.0.0", port=8000, reload="PYBALL_DEV" in os.environ
        )
    except KeyboardInterrupt:
        logger.info("Stoping the application...")


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


if __name__ == "__main__":
    main()
