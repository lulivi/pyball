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
"""FastAPI application factory."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pyball.application.meetup.finish_match import MeetupAlreadyClosedError
from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.errors import MeetupNotFoundError

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.settings import Settings

logger = logging.getLogger(__name__)


class GoalEventInput(BaseModel):
    """Pydantic model for a single goal event from the frontend."""

    scorer: str
    assistant: str | None
    team: str
    timestamp: str


class FinalScore(BaseModel):
    """Pydantic model for the final score."""

    A: int
    B: int


class FinishMatchInput(BaseModel):
    """Pydantic model for the POST /api/match/finish request body."""

    meetup_date: str
    events: list[GoalEventInput]
    finalScore: FinalScore


def create_app(  # pylint: disable=unused-argument
    container: "Container",
    notifier: MatchNotifier,
    settings: "Settings",
    static_dir: Path = Path("static"),
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        container: DI container with repositories and use cases.
        notifier: Notifier called after match events.
        settings: Application settings.
        static_dir: Path to the static files directory.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="PyBall Match API")

    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and notify via the configured notifier."""
        logger.info(
            "finish_match called: meetup_date=%s, finalScore=%s",
            body.meetup_date,
            body.finalScore,
        )
        use_case = container.finish_match()
        events = [e.model_dump() for e in body.events]
        try:
            meetup = use_case.execute(
                body.meetup_date, events, {"A": body.finalScore.A, "B": body.finalScore.B}
            )
            logger.info("finish_match: meetup result set: %s", meetup.result)
        except MeetupNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meetup not found") from exc
        except MeetupAlreadyClosedError as exc:
            raise HTTPException(status_code=409, detail="Match already closed") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        await notifier.on_match_closed(meetup)

        return {
            "meetup_date": body.meetup_date,
            "score_a": meetup.result.score_a,
            "score_b": meetup.result.score_b,
        }

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
