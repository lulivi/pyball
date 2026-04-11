from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import Message, Update, User
from telegram.ext import ContextTypes

from pyball.bot.handlers.player import (
    change_group_handler,
    delete_player_handler,
    link_player_handler,
    list_players_handler,
    new_player_handler,
    rename_player_handler,
    unlink_player_handler,
)
from pyball.domain.player.errors import PlayerAlreadyExistsError, PlayerNotFoundError


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    message = AsyncMock(spec=Message)
    update.message = message
    user = MagicMock(spec=User)
    user.id = 12345
    update.effective_user = user
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    context.bot_data = {"settings": settings}
    return context


@pytest.mark.asyncio
async def test_new_player_handler_success(mock_update, mock_context):
    mock_context.args = ["Luis", "regular"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    container.create_player().execute.return_value = mock_player

    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        r"Player `Luis` created as regular\!", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_new_player_handler_duplicate_raises(mock_update, mock_context):
    mock_context.args = ["Luis", "regular"]

    container = MagicMock()
    container.create_player().execute.side_effect = PlayerAlreadyExistsError(
        "Player already exists"
    )

    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    assert mock_update.message.reply_text.called
    args, kwargs = mock_update.message.reply_text.call_args
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_rename_player_handler_success(mock_update, mock_context):
    mock_context.args = ["pid1", "New Name"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "New Name"
    container.rename_player().execute.return_value = mock_player

    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        r"Player renamed to `New Name`\!", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_delete_player_handler_success(mock_update, mock_context):
    mock_context.args = ["pid1"]

    container = MagicMock()
    mock_context.bot_data["container"] = container

    await delete_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with("Player deleted!")


@pytest.mark.asyncio
async def test_list_players_handler_success(mock_update, mock_context):
    container = MagicMock()
    mock_player1 = MagicMock()
    mock_player1.name = "Luis"
    mock_player1.group = "regular"
    mock_player2 = MagicMock()
    mock_player2.name = "Pedro"
    mock_player2.group = "substitute"

    container.player_repository.find_all.return_value = [mock_player1, mock_player2]

    mock_context.bot_data["container"] = container

    await list_players_handler(mock_update, mock_context)

    assert mock_update.message.reply_text.called
    args, _ = mock_update.message.reply_text.call_args
    assert "*Jugadores:*" in args[0]
    assert r"*Titulares \(1\):*" in args[0]
    assert r"- `Luis`" in args[0]
    assert r"*Suplentes \(1\):*" in args[0]
    assert r"- `Pedro`" in args[0]


@pytest.mark.asyncio
async def test_change_group_handler_success(mock_update, mock_context):
    mock_context.args = ["Luis", "substitute"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    container.change_player_group().execute.return_value = mock_player
    container.player_repository.find_all.return_value = [mock_player]

    from pyball.domain.player.models import PlayerId

    mock_player.player_id = PlayerId.generate()

    mock_context.bot_data["container"] = container

    await change_group_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        r"Player `Luis` changed to `substitute`\!", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_link_player_handler_success(mock_update, mock_context):
    mock_context.args = ["Luis", "12345"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    from pyball.domain.player.models import PlayerId

    mock_player.player_id = PlayerId.generate()
    container.player_repository.find_all.return_value = [mock_player]

    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"] = MagicMock()

    from pyball.infrastructure.telegram.mapping import TelegramMappingStore

    with pytest.MonkeyPatch.context() as m:
        m.setattr("pyball.bot.handlers.player.TelegramMappingStore", MagicMock())
        await link_player_handler(mock_update, mock_context)

    assert mock_update.message.reply_text.called


@pytest.mark.asyncio
async def test_unlink_player_handler_success(mock_update, mock_context):
    mock_context.args = ["12345"]

    mock_context.bot_data["settings"] = MagicMock()

    from pyball.infrastructure.telegram.mapping import TelegramMappingStore

    mock_mapping_store = MagicMock()
    mock_mapping_store.get_player_id.return_value = "player1"

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping_store),
        )

        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        r"Link for Telegram ID `12345` removed\!", parse_mode="MarkdownV2"
    )
