"""Integration tests for player bot handlers."""

import pytest

from pyball.domain.player.models import Player
from pyball.infrastructure.telegram.bot.handlers.player import (
    link_player_handler,
    unlink_player_handler,
)
from pyball.infrastructure.telegram.mapping import TelegramMappingStore

# pylint: disable=redefined-outer-name


@pytest.mark.asyncio
async def test_link_player_writes_mapping(bot_update, bot_context):
    """Link a player and verify the real TelegramMappingStore has the entry."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = ["Luis,", "55555"]

    await link_player_handler(bot_update, bot_context)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")
    assert store.get_player_id(55555) == str(player.id.value)


@pytest.mark.asyncio
async def test_unlink_player_removes_mapping(bot_update, bot_context):
    """Unlink a player and verify the mapping entry is removed."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.data_dir / "bot" / "telegram-uuid.json")
    store.set_player_id(55555, str(player.id.value))

    bot_context.args = ["Luis"]

    await unlink_player_handler(bot_update, bot_context)

    assert store.get_player_id(55555) is None
