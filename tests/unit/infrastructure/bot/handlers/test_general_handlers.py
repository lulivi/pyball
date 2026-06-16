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
)


def _build_app() -> Application:
    app = Application.builder().token("123:ABC").build()
    setup_player_handlers(app)
    setup_meetup_handlers(app)
    setup_general_handlers(app)
    return app


def test_registered_commands_match_descriptions():
    app = _build_app()
    assert registered_commands(app) == set(COMMAND_DESCRIPTIONS)


def test_build_bot_commands_one_per_description_in_order():
    commands = build_bot_commands()
    assert commands == [
        BotCommand(name, desc) for name, (desc, _cat) in COMMAND_DESCRIPTIONS.items()
    ]
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
    assert r"`/new_player`" in text
    assert r"`/change_location`" in text
    assert update.message.reply_text.call_args.kwargs["parse_mode"] == ParseMode.MARKDOWN_V2
