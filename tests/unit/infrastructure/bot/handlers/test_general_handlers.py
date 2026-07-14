"""Tests for general bot handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import BotCommand
from telegram.constants import ParseMode
from telegram.ext import Application

from pyball.infrastructure.telegram.bot.handlers import (
    setup_general_handlers,
    setup_meetup_handlers,
    setup_player_handlers,
)
from pyball.infrastructure.telegram.bot.handlers.general import (
    COMMAND_DESCRIPTIONS,
    build_bot_commands,
    help_handler,
    register_bot_commands,
    registered_commands,
    short_alias,
)


def _build_app() -> Application:
    app = Application.builder().token("123:ABC").build()
    setup_player_handlers(app)
    setup_meetup_handlers(app)
    setup_general_handlers(app)
    return app


def test_registered_commands_match_descriptions():
    app = _build_app()
    expected = set(COMMAND_DESCRIPTIONS)
    expected |= {short_alias(n) for n in COMMAND_DESCRIPTIONS if short_alias(n)}
    assert registered_commands(app) == expected


def test_build_bot_commands_one_per_description_in_order():
    commands = build_bot_commands()
    assert commands == [BotCommand(name, desc) for name, desc in COMMAND_DESCRIPTIONS.items()]
    assert all(isinstance(c, BotCommand) for c in commands)


@pytest.mark.asyncio
async def test_register_bot_commands_calls_set_my_commands():
    bot = AsyncMock()
    await register_bot_commands(bot)
    bot.set_my_commands.assert_called_once_with(build_bot_commands())


@pytest.mark.asyncio
async def test_help_handler_renders_categories():
    update = MagicMock()
    update.message = AsyncMock()

    await help_handler(update, MagicMock())

    text = update.message.reply_text.call_args.args[0]
    assert "*Player:*" in text
    assert r"`/player_new`" in text
    assert r"`/meetup_search`" in text
    assert update.message.reply_text.call_args.kwargs["parse_mode"] == ParseMode.MARKDOWN_V2


def test_short_alias_derivation():
    assert short_alias("player_change_group") == "p_change_group"
    assert short_alias("meetup_change_date") == "m_change_date"
    assert short_alias("help") is None
