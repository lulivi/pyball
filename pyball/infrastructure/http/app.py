"""FastAPI application factory."""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import telegram
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pyball.application.meetup.compute_stats import ComputeStats
from pyball.application.meetup.finish_match import MeetupAlreadyClosedError
from pyball.bot.handlers.meetup import close_match_messages
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram import TelegramMessageStore

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.settings import Settings

logger = logging.getLogger(__name__)


async def _post_match_stats(
    bot: "telegram.Bot",
    container: "Container",
    settings: "Settings",
) -> None:
    """Compute and post the season stats image to the regulars stats topic.

    Runs as a background asyncio task. Errors are logged and swallowed so
    they never affect the match-finish response.

    Args:
        bot: Telegram Bot instance for sending photos.
        container: DI container with repositories.
        settings: Application settings for chat/thread IDs.
    """
    try:
        report = ComputeStats(
            container.meetup_repository,
            container.player_repository,
            container.legacy_stats,
        ).execute()
        season_png = await StatsHtmlRenderer().render(report, scope="season")

        stats_thread_id = settings.telegram.regulars.stats_thread_id or None
        chat_id = settings.telegram.regulars.chat_id

        await bot.send_photo(
            chat_id=chat_id,
            photo=season_png,
            caption="📊 Esta temporada",
            message_thread_id=int(stats_thread_id) if stats_thread_id else None,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error posting match stats")


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


def create_app(
    container: "Container",
    bot: telegram.Bot,
    settings: "Settings",
    static_dir: Path = Path("static"),
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        container: DI container with repositories and use cases.
        bot: Telegram Bot instance for editing messages after match.
        settings: Application settings (for message store path and chat config).
        static_dir: Path to the static files directory.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(title="PyBall Match API")

    @app.post("/api/match/finish")
    async def finish_match(body: FinishMatchInput):
        """Record match result and update Telegram callup messages."""
        use_case = container.finish_match()
        events = [e.model_dump() for e in body.events]
        try:
            meetup = use_case.execute(
                body.meetup_date, events, {"A": body.finalScore.A, "B": body.finalScore.B}
            )
        except MeetupNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meetup not found") from exc
        except MeetupAlreadyClosedError as exc:
            raise HTTPException(status_code=409, detail="Match already closed") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        all_players = container.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}
        player_groups = {str(p.id.value): p.group for p in all_players}

        message_store = TelegramMessageStore(settings.paths.bot_messages_file)
        await close_match_messages(
            bot,
            message_store,
            meetup,
            player_names,
            player_groups,
            team_display_names=settings.pyball.team_display_names,
        )

        asyncio.create_task(_post_match_stats(bot, container, settings))

        return {
            "meetup_date": body.meetup_date,
            "score_a": meetup.result.score_a,
            "score_b": meetup.result.score_b,
        }

    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
