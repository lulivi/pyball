"""Integration tests for player bot handlers."""

import pytest

from pyball.infrastructure.telegram.bot.handlers.player import (
    change_group_handler,
    delete_player_handler,
    link_player_handler,
    list_players_handler,
    new_player_handler,
    rename_player_handler,
    unlink_player_handler,
)
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram.mapping import TelegramMappingStore

# pylint: disable=redefined-outer-name


@pytest.mark.asyncio
async def test_new_player_persists(bot_update, bot_context):
    """Create a new player and verify it exists in the real repo."""
    bot_context.args = ["Luis", "regular"]

    await new_player_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    player = container.player_repository.find_by_name("Luis")
    assert player is not None
    assert player.group == "regular"


@pytest.mark.asyncio
async def test_new_player_duplicate_replies_spanish_error(bot_update, bot_context):
    """Reply with Spanish error when player already exists."""
    bot_context.args = ["Luis", "regular"]
    await new_player_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_player_handler(bot_update, bot_context)

    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "ya existe" in text.lower()


@pytest.mark.asyncio
async def test_rename_player_persists(bot_update, bot_context):
    """Rename a player and verify the updated name is in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = [str(player.id.value), "Carlos"]

    await rename_player_handler(bot_update, bot_context)

    found = container.player_repository.find_by_id(player.id)
    assert found.name == "Carlos"


@pytest.mark.asyncio
async def test_delete_player_removes_from_repo(bot_update, bot_context):
    """Delete a player and verify it is absent from the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("ToDelete", "regular")
    container.player_repository.save(player)

    bot_context.args = [str(player.id.value)]

    await delete_player_handler(bot_update, bot_context)

    found = container.player_repository.find_by_id(player.id)
    assert found is None


@pytest.mark.asyncio
async def test_list_players_includes_names(bot_update, bot_context):
    """List players and verify the reply includes names from the real repo."""
    container = bot_context.bot_data["container"]
    container.player_repository.save(Player.create("Ana", "regular"))
    container.player_repository.save(Player.create("Pedro", "substitute"))

    await list_players_handler(bot_update, bot_context)

    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "Ana" in text
    assert "Pedro" in text


@pytest.mark.asyncio
async def test_change_group_persists(bot_update, bot_context):
    """Change a player group and verify the update is in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = ["Luis", "substitute"]

    await change_group_handler(bot_update, bot_context)

    found = container.player_repository.find_by_name("Luis")
    assert found.group == "substitute"


@pytest.mark.asyncio
async def test_link_player_writes_mapping(bot_update, bot_context):
    """Link a player and verify the real TelegramMappingStore has the entry."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = ["Luis", "55555"]

    await link_player_handler(bot_update, bot_context)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.bot_mappings_file)
    assert store.get_player_id(55555) == str(player.id.value)


@pytest.mark.asyncio
async def test_unlink_player_removes_mapping(bot_update, bot_context):
    """Unlink a player and verify the mapping entry is removed."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.bot_mappings_file)
    store.set_player_id(55555, str(player.id.value))

    bot_context.args = ["55555"]

    await unlink_player_handler(bot_update, bot_context)

    assert store.get_player_id(55555) is None


@pytest.mark.asyncio
async def test_list_players_empty_repo(bot_update, bot_context):
    """list_players_handler with an empty repo replies with 'No players found.'"""
    await list_players_handler(bot_update, bot_context)

    call = bot_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert text == "No hay jugadores registrados."
