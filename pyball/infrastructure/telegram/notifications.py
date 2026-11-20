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
"""Telegram notification implementations for match and meetup events."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import telegram
from telegram.constants import ParseMode

from pyball.application.meetup.compute_stats import ComputeStats
from pyball.application.notifier import MatchNotifier
from pyball.domain.meetup.models import Meetup
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram.formatters import (
    build_main_keyboard,
    build_subs_keyboard,
    escape_summary_for_telegram,
    format_display,
    format_main_message,
    format_subs_message,
)
from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore

if TYPE_CHECKING:
    from pyball.application.container import Container
    from pyball.domain.player.models import Player
    from pyball.infrastructure.telegram.settings import TelegramAppSettings

logger = logging.getLogger(__name__)


class TelegramMatchNotifier(MatchNotifier):
    """Telegram implementation of MatchNotifier."""

    def __init__(
        self,
        bot: telegram.Bot,
        settings: "TelegramAppSettings",
        container: "Container",
    ) -> None:
        """Initialize with Telegram bot, application settings, and DI container."""
        self._bot = bot
        self._settings = settings
        self._container = container

    async def on_meetup_created(self, meetup: Meetup) -> None:
        """Handle a brand-new meetup by posting the regulars callup and the activity line.

        The substitutes chat is never notified here: it is called only when a
        substitute search opens, so regulars get priority before subs are searched.
        """
        await _send_regulars_callup_message(self._bot, self._settings, self._container, meetup)
        date_str = format_display(meetup.date, self._settings.pyball.display_date_format)
        await _send_activity_message(
            self._bot,
            self._settings,
            f"🆕 *Convocatoria creada* — nueva convocatoria para el `{date_str}`\\.",
        )

    async def on_meetup_updated(self, meetup: Meetup) -> None:
        """Handle a meetup update by refreshing platform messages.

        The join/leave keyboard is omitted once teams exist — signup is
        closed automatically the moment teams are generated.
        """
        await refresh_callup_messages(
            self._bot,
            self._settings,
            self._container,
            meetup,
            include_keyboard=meetup.is_signup_open(),
        )

    async def on_meetup_date_changed(self, old_date: datetime, meetup: Meetup) -> None:
        """Handle a meetup date change by re-keying tracked messages and refreshing them."""
        store = TelegramMessageStore(self._settings.paths.data_dir / "bot" / "messages.json")
        store.rename_date(old_date, meetup.date)
        await refresh_callup_messages(
            self._bot,
            self._settings,
            self._container,
            meetup,
            include_keyboard=meetup.is_signup_open(),
        )

    async def on_meetup_cancelled(self, meetup: Meetup) -> None:
        """Edit a cancelled meetup's messages and post the cancellation to the activity feed."""
        await _cancel_callup_messages(self._bot, self._settings, self._container, meetup)
        date_str = format_display(meetup.date, self._settings.pyball.display_date_format)
        await _send_activity_message(
            self._bot,
            self._settings,
            f"🚫 *Convocatoria cancelada* — se ha cancelado la convocatoria del `{date_str}`\\.",
        )

    async def on_match_closed(self, meetup: Meetup) -> None:
        """Handle a closed match by updating messages, clearing tracking, and posting stats."""
        await refresh_callup_messages(
            self._bot, self._settings, self._container, meetup, include_keyboard=False
        )
        message_store = TelegramMessageStore(
            self._settings.paths.data_dir / "bot" / "messages.json"
        )
        message_store.delete_message(meetup.date, "regular")
        message_store.delete_message(meetup.date, "substitute")
        date_str = format_display(meetup.date, self._settings.pyball.display_date_format)
        await _send_activity_message(
            self._bot,
            self._settings,
            f"🏁 *Convocatoria cerrada* — la convocatoria del `{date_str}` ha finalizado\\.",
        )
        asyncio.create_task(_post_match_stats(self._bot, self._container, self._settings))

    async def on_match_edited(self, meetup: Meetup) -> None:
        """Announce a corrected result with a new message and refresh the stats image.

        The original callup messages were untracked when the match closed, so
        editing them is impossible — a fresh message is sent instead.
        """
        player_names = {
            str(p.id.value): p.name for p in self._container.player_repository.find_all()
        }
        summary = self._container.format_match_summary().execute(
            meetup,
            player_names,
            team_colors=self._settings.pyball.team_colors,
            team_emojis=self._settings.pyball.team_emojis,
            legacy_stats=self._container.legacy_stats,
        )
        meetups = self._settings.telegram.regulars.meetups
        try:
            await self._bot.send_message(
                chat_id=meetups.chat_id,
                text=f"✏️ Resultado corregido\n\n{escape_summary_for_telegram(summary)}",
                message_thread_id=meetups.message_thread_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            asyncio.create_task(_post_match_stats(self._bot, self._container, self._settings))
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error sending corrected result message: %s", error)

    async def on_substitute_search_opened(self, meetup: Meetup) -> None:
        """Post the substitutes callup, if a substitutes chat is configured."""
        if not self._settings.telegram.substitutes.meetups:
            return
        try:
            await send_substitutes_message(self._bot, self._settings, self._container, meetup)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error sending substitutes message: %s", error)

    async def on_player_joined(
        self, meetup: Meetup, player: "Player", is_substitute: bool
    ) -> None:
        """Handle a player joining a meetup by posting to the activity chat."""
        status = "suplente" if is_substitute else "titular"
        date_str = format_display(meetup.date, self._settings.pyball.display_date_format)
        name = _escape_code_span(player.name)
        text = (
            f"✅ *Alta* — `{name}` se apunta como {status} a la convocatoria del "
            f"`{date_str}`\\."
        )
        await _send_activity_message(self._bot, self._settings, text)

    async def on_player_left(self, meetup: Meetup, player: "Player", is_substitute: bool) -> None:
        """Handle a player leaving a meetup by posting to the activity chat."""
        status = "suplente" if is_substitute else "titular"
        date_str = format_display(meetup.date, self._settings.pyball.display_date_format)
        name = _escape_code_span(player.name)
        text = (
            f"❌ *Baja* — `{name}` se desapunta como {status} de la convocatoria del "
            f"`{date_str}`\\."
        )
        await _send_activity_message(self._bot, self._settings, text)


async def refresh_callup_messages(
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    container: "Container",
    meetup: Meetup,
    include_keyboard: bool = True,
) -> None:
    """Edit the existing callup messages to reflect the current meetup state.

    Args:
        bot: Telegram Bot instance.
        settings: Application settings (for message store path and chat config).
        container: DI container with repositories.
        meetup: Meetup to display.
        include_keyboard: Whether to include join/leave buttons (default True).
    """
    player_repo = container.player_repository
    all_players = player_repo.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}

    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    date_fmt = settings.pyball.display_date_format

    regular_tracking = store.get_message(meetup.date, "regular")
    if regular_tracking:
        text = format_main_message(
            meetup,
            player_names,
            team_colors=settings.pyball.team_colors,
            team_emojis=settings.pyball.team_emojis,
            date_fmt=date_fmt,
            legacy_stats=container.legacy_stats,
        )
        kb = build_main_keyboard(meetup.date) if include_keyboard else None
        try:
            await bot.edit_message_text(
                chat_id=regular_tracking.chat_id,
                message_id=regular_tracking.message_id,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit regulars message: %s", error)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error editing regulars message: %s", error)

    sub_tracking = store.get_message(meetup.date, "substitute")
    if sub_tracking:
        subs_text = format_subs_message(
            meetup,
            player_names,
            player_groups,
            team_colors=settings.pyball.team_colors,
            team_emojis=settings.pyball.team_emojis,
            date_fmt=date_fmt,
        )
        kb = (
            build_subs_keyboard(meetup.date)
            if include_keyboard and meetup.substitute_search
            else None
        )
        try:
            await bot.edit_message_text(
                chat_id=sub_tracking.chat_id,
                message_id=sub_tracking.message_id,
                text=subs_text,
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit substitutes message: %s", error)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error editing substitutes message: %s", error)


async def send_substitutes_message(
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    container: "Container",
    meetup: Meetup,
) -> None:
    """Send the substitutes callup to the substitutes chat and track it.

    The join/leave keyboard is attached only while the substitute search is open.
    """
    all_players = container.player_repository.find_all()
    text = format_subs_message(
        meetup,
        {str(p.id.value): p.name for p in all_players},
        {str(p.id.value): p.group for p in all_players},
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
    )
    keyboard = build_subs_keyboard(meetup.date) if meetup.substitute_search else None
    subs = settings.telegram.substitutes.meetups
    msg = await bot.send_message(
        chat_id=subs.chat_id,
        text=text,
        reply_markup=keyboard,
        message_thread_id=subs.message_thread_id,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json").save_message(
        meetup.date,
        "substitute",
        MessageTracking(
            chat_id=subs.chat_id, thread_id=subs.message_thread_id, message_id=msg.message_id
        ),
    )


async def _cancel_callup_messages(
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    container: "Container",
    meetup: Meetup,
) -> None:
    """Edit tracked callup messages to show cancellation, then clear their tracking."""
    player_repo = container.player_repository
    all_players = player_repo.find_all()
    player_names = {str(p.id.value): p.name for p in all_players}
    player_groups = {str(p.id.value): p.group for p in all_players}

    store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
    date_fmt = settings.pyball.display_date_format
    cancelled_prefix = "🚫 *CANCELADO*\n\n"

    regular_tracking = store.get_message(meetup.date, "regular")
    if regular_tracking:
        text = cancelled_prefix + format_main_message(
            meetup,
            player_names,
            team_colors=settings.pyball.team_colors,
            team_emojis=settings.pyball.team_emojis,
            date_fmt=date_fmt,
        )
        try:
            await bot.edit_message_text(
                chat_id=regular_tracking.chat_id,
                message_id=regular_tracking.message_id,
                text=text,
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit regulars message on cancel: %s", error)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error editing regulars message on cancel: %s", error)

    sub_tracking = store.get_message(meetup.date, "substitute")
    if sub_tracking:
        subs_text = cancelled_prefix + format_subs_message(
            meetup,
            player_names,
            player_groups,
            team_colors=settings.pyball.team_colors,
            team_emojis=settings.pyball.team_emojis,
            date_fmt=date_fmt,
        )
        try:
            await bot.edit_message_text(
                chat_id=sub_tracking.chat_id,
                message_id=sub_tracking.message_id,
                text=subs_text,
                reply_markup=None,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.BadRequest as error:
            logger.warning("Could not edit substitutes message on cancel: %s", error)
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error editing substitutes message on cancel: %s", error)

    store.delete_message(meetup.date, "regular")
    store.delete_message(meetup.date, "substitute")


async def _send_regulars_callup_message(
    bot: telegram.Bot,
    settings: "TelegramAppSettings",
    container: "Container",
    meetup: Meetup,
) -> None:
    """Send the initial callup message to the regulars chat and track it."""
    player_names = {str(p.id.value): p.name for p in container.player_repository.find_all()}
    text = format_main_message(
        meetup,
        player_names,
        team_colors=settings.pyball.team_colors,
        team_emojis=settings.pyball.team_emojis,
        date_fmt=settings.pyball.display_date_format,
    )
    keyboard = build_main_keyboard(meetup.date)
    meetups = settings.telegram.regulars.meetups

    try:
        msg = await bot.send_message(
            chat_id=meetups.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=meetups.message_thread_id,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        store = TelegramMessageStore(settings.paths.data_dir / "bot" / "messages.json")
        store.save_message(
            meetup.date,
            "regular",
            MessageTracking(
                chat_id=meetups.chat_id,
                thread_id=meetups.message_thread_id,
                message_id=msg.message_id,
            ),
        )
    except telegram.error.TelegramError as error:
        logger.error("Error sending regulars message (Telegram): %s", error)
    except Exception as error:  # pylint: disable=broad-except
        logger.exception("Error sending regulars message: %s", error)


async def _post_match_stats(
    bot: telegram.Bot,
    container: "Container",
    settings: "TelegramAppSettings",
) -> None:
    """Compute and post the season stats image to the regulars stats topic.

    Runs as a background asyncio task. Does nothing when no stats chat is
    configured. Errors are logged and swallowed.
    """
    stats = settings.telegram.regulars.stats
    if not stats:
        return
    try:
        report = ComputeStats(
            container.meetup_repository,
            container.player_repository,
            container.legacy_stats,
        ).execute()
        season_png = await StatsHtmlRenderer().render(report, scope="season")
        await bot.send_photo(
            chat_id=stats.chat_id,
            photo=season_png,
            caption="📊 Estadísticas",
            message_thread_id=stats.message_thread_id,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error posting match stats")


def _escape_code_span(text: str) -> str:
    """Escape backslash and backtick so text is safe inside a MarkdownV2 code span."""
    return text.replace("\\", "\\\\").replace("`", "\\`")


async def _send_activity_message(
    bot: telegram.Bot, settings: "TelegramAppSettings", text: str
) -> None:
    """Send a message to the activity chat, if one is configured."""
    activity = settings.telegram.management.activity
    if not activity:
        return
    try:
        await bot.send_message(
            chat_id=activity.chat_id,
            text=text,
            message_thread_id=activity.message_thread_id,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as error:  # pylint: disable=broad-except
        logger.error("Error sending activity message: %s", error)
