"""The callup messages in the regulars and substitutes chats, kept in step with PyBall.

Each event from PyBall's stream sends, edits or cancels them. A Telegram error is logged
and the event counts as handled: a message that cannot be edited stays as it was. A
PyBall error propagates, so the plugin restarts and handles the event again.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import telegram
from pyball_client import Api
from telegram.constants import ParseMode

from pyball_telegram.api import PLAYERS, STATS, SUMMARY, Event, Meetup, Settings
from pyball_telegram.config import Chat, Config
from pyball_telegram.formatters import (
    escape_summary,
    format_main_message,
    format_subs_message,
    main_keyboard,
    subs_keyboard,
)
from pyball_telegram.state import ChatType, MessageStore, TrackedMessage

logger = logging.getLogger(__name__)

_CANCELLED = "🚫 *CANCELADO*\n\n"


@dataclass
class Callups:
    """Posts and updates the callups of each meetup, and the stats after a match."""

    bot: telegram.Bot
    api: Api
    config: Config
    settings: Settings

    @property
    def messages(self) -> MessageStore:
        """Return the store of tracked messages."""
        return MessageStore(self.config.messages_file)

    async def handle(self, event: Event) -> None:
        """Bring the callups up to date with ``event``."""
        meetup = event.meetup
        match event.kind:
            case "meetup.created":
                await self.send_regulars(meetup)
            case "meetup.updated":
                await self.refresh(meetup, keyboard=meetup.signup_open())
            case "meetup.date_changed" if event.previous_date is not None:
                self.messages.rename_date(event.previous_date, meetup.date)
                await self.refresh(meetup, keyboard=meetup.signup_open())
            case "meetup.cancelled":
                await self.refresh(meetup, keyboard=False, prefix=_CANCELLED)
                self._untrack(meetup)
            case "match.closed":
                await self.refresh(meetup, keyboard=False)
                self._untrack(meetup)
                await self.post_stats()
            case "match.edited":
                await self._announce_correction(meetup)
            case "substitute_search.opened" if self.config.substitutes_meetups:
                await self.send_substitutes(meetup)
            case "player.joined" | "player.left":
                await self.refresh(meetup)

    async def send_regulars(self, meetup: Meetup) -> None:
        """Post a new regulars callup for ``meetup`` and track it."""
        names, _ = await self.players()
        text = format_main_message(meetup, names, self._date_fmt, await self._summary(meetup))
        keyboard = main_keyboard(meetup.date) if meetup.signup_open() else None
        await self._send(meetup, "regular", self.config.regulars_meetups, text, keyboard)

    async def send_substitutes(self, meetup: Meetup) -> None:
        """Post a new substitutes callup for ``meetup`` and track it.

        The buttons are attached only while the substitute search is open.
        """
        names, groups = await self.players()
        text = format_subs_message(meetup, names, groups, self._date_fmt)
        keyboard = subs_keyboard(meetup.date) if meetup.substitute_search else None
        await self._send(meetup, "substitute", self.config.substitutes_meetups, text, keyboard)

    async def refresh(self, meetup: Meetup, keyboard: bool = True, prefix: str = "") -> None:
        """Edit the tracked callups of ``meetup`` to show it as it is now."""
        regular = self.messages.get(meetup.date, "regular")
        substitute = self.messages.get(meetup.date, "substitute")
        if regular is None and substitute is None:
            return
        names, groups = await self.players()
        if regular is not None:
            summary = await self._summary(meetup)
            text = prefix + format_main_message(meetup, names, self._date_fmt, summary)
            markup = main_keyboard(meetup.date) if keyboard else None
            await self._edit(regular, text, markup)
        if substitute is not None:
            text = prefix + format_subs_message(meetup, names, groups, self._date_fmt)
            markup = subs_keyboard(meetup.date) if keyboard and meetup.substitute_search else None
            await self._edit(substitute, text, markup)

    async def post_stats(self) -> None:
        """Post the season stats image to the stats chat, if one is configured."""
        chat = self.config.regulars_stats
        if not chat:
            return
        png = await self.api.call(STATS, params={"scope": "season"})
        try:
            await self.bot.send_photo(
                chat_id=chat.chat_id,
                photo=png,
                caption="📊 Estadísticas",
                message_thread_id=chat.thread_id,
            )
        except telegram.error.TelegramError as error:
            logger.error("Could not post the stats: %s", error)

    async def _announce_correction(self, meetup: Meetup) -> None:
        """Post a corrected result as a new message: the old callups are no longer tracked."""
        chat = self.config.regulars_meetups
        text = f"✏️ Resultado corregido\n\n{escape_summary(await self._summary(meetup))}"
        try:
            await self.bot.send_message(
                chat_id=chat.chat_id,
                text=text,
                message_thread_id=chat.thread_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.TelegramError as error:
            logger.error("Could not post the corrected result: %s", error)
            return
        await self.post_stats()

    async def _send(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        meetup: Meetup,
        chat_type: ChatType,
        chat: Chat,
        text: str,
        keyboard: telegram.InlineKeyboardMarkup | None,
    ) -> None:
        try:
            sent = await self.bot.send_message(
                chat_id=chat.chat_id,
                text=text,
                reply_markup=keyboard,
                message_thread_id=chat.thread_id,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.TelegramError as error:
            logger.error("Could not post the %s callup: %s", chat_type, error)
            return
        self.messages.save(
            meetup.date, chat_type, TrackedMessage(chat.chat_id, sent.message_id, chat.thread_id)
        )

    async def _edit(
        self,
        message: TrackedMessage,
        text: str,
        keyboard: telegram.InlineKeyboardMarkup | None,
    ) -> None:
        try:
            await self.bot.edit_message_text(
                chat_id=message.chat_id,
                message_id=message.message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except telegram.error.TelegramError as error:
            logger.warning("Could not edit message %s: %s", message.message_id, error)

    def _untrack(self, meetup: Meetup) -> None:
        self.messages.delete(meetup.date, "regular")
        self.messages.delete(meetup.date, "substitute")

    async def players(self) -> tuple[dict[str, str], dict[str, str]]:
        """Return every player's name and group, by id."""
        players = await self.api.call(PLAYERS)
        return {p.id: p.name for p in players}, {p.id: p.group for p in players}

    async def _summary(self, meetup: Meetup) -> str:
        """Return the result summary of a closed meetup, empty for an open one."""
        if not meetup.closed:
            return ""
        return (await self.api.call(SUMMARY, meetup_id=meetup.id)).text

    @property
    def _date_fmt(self) -> str:
        return self.settings.display_date_format
