from unittest.mock import MagicMock

import pytest
from telegram.constants import ReactionEmoji

from pyball.infrastructure.telegram.bot.handlers.player import (
    link_player_handler,
    unlink_player_handler,
)


@pytest.mark.asyncio
async def test_link_player_handler_success(mock_update, mock_context):
    mock_context.args = ["Luis,", "12345"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"

    from pyball.domain.player.models import PlayerId

    mock_player.player_id = PlayerId.generate()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"] = MagicMock()

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = None  # player not yet linked

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_unlink_player_handler_success(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    mock_context.args = ["Luis"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"] = MagicMock()

    mock_mapping_store = MagicMock()
    mock_mapping_store.get_telegram_id.return_value = 12345

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping_store),
        )
        await unlink_player_handler(mock_update, mock_context)

    mock_mapping_store.delete_player_id.assert_called_once_with(12345)
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_link_player_handler_non_numeric_id(mock_update, mock_context):
    mock_context.args = ["Luis,", "abc"]
    mock_context.bot_data["container"] = MagicMock()

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore", MagicMock()
        )
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "ID de Telegram no válido. Debe ser un número."
    )


@pytest.mark.asyncio
async def test_link_player_handler_already_linked_same(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis,", "12345"]

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = str(player_id.value)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Este ID de Telegram ya está vinculado a este jugador."
    )


@pytest.mark.asyncio
async def test_link_player_handler_already_linked_other(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis,", "12345"]

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = str(PlayerId.generate().value)  # different player

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    (text, *_), _ = mock_update.message.reply_text.call_args
    assert "vinculado a otro jugador" in text


@pytest.mark.asyncio
async def test_unlink_player_handler_not_linked(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = PlayerId.generate()

    mock_context.args = ["Luis"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"] = MagicMock()

    mock_mapping = MagicMock()
    mock_mapping.get_telegram_id.return_value = None

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.infrastructure.telegram.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Este jugador no está vinculado a ningún ID de Telegram."
    )
