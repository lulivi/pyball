from unittest.mock import MagicMock

import pytest

from pyball.bot.handlers.player import (
    change_group_handler,
    delete_player_handler,
    link_player_handler,
    list_players_handler,
    new_player_handler,
    rename_player_handler,
    unlink_player_handler,
)
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)


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
        text=r"Player `Luis` created as regular\!", parse_mode="MarkdownV2"
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
        text=r"Player renamed to `New Name`\!", parse_mode="MarkdownV2"
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
    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "*Jugadores:*" in text
    assert r"*Titulares \(1\):*" in text
    assert r"- `Luis`" in text
    assert r"*Suplentes \(1\):*" in text
    assert r"- `Pedro`" in text


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
        text=r"Player `Luis` changed to `substitute`\!", parse_mode="MarkdownV2"
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
        text=r"Link for Telegram ID `12345` removed\!", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_new_player_handler_invalid_group(mock_update, mock_context):
    mock_context.args = ["Luis", "vip"]
    mock_context.bot_data["container"] = MagicMock()

    await new_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        text="Group must be `regular` or `substitute`", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_rename_player_handler_invalid_id(mock_update, mock_context):
    mock_context.args = ["bad-id", "New Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = InvalidPlayerIdError("bad id")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Invalid player ID format.")


@pytest.mark.asyncio
async def test_rename_player_handler_not_found(mock_update, mock_context):
    mock_context.args = ["pid1", "New Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = PlayerNotFoundError("not found")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Player not found.")


@pytest.mark.asyncio
async def test_rename_player_handler_name_taken(mock_update, mock_context):
    mock_context.args = ["pid1", "Existing Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = NameAlreadyTakenError("name taken")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    _, kwargs = mock_update.message.reply_text.call_args
    assert kwargs.get("parse_mode") == "HTML"


@pytest.mark.asyncio
async def test_link_player_handler_non_numeric_id(mock_update, mock_context):
    mock_context.args = ["Luis", "abc"]
    mock_context.bot_data["container"] = MagicMock()

    with pytest.MonkeyPatch.context() as m:
        m.setattr("pyball.bot.handlers.player.TelegramMappingStore", MagicMock())
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Invalid telegram_id. Must be a number.")


@pytest.mark.asyncio
async def test_link_player_handler_already_linked_same(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis", "12345"]

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
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "This Telegram ID is already linked to this player."
    )


@pytest.mark.asyncio
async def test_link_player_handler_already_linked_other(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis", "12345"]

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
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    (text, *_), _ = mock_update.message.reply_text.call_args
    assert "linked to another player" in text


@pytest.mark.asyncio
async def test_unlink_player_handler_non_numeric_id(mock_update, mock_context):
    mock_context.args = ["abc"]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("pyball.bot.handlers.player.TelegramMappingStore", MagicMock())
        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Invalid telegram_id. Must be a number.")


@pytest.mark.asyncio
async def test_unlink_player_handler_not_linked(mock_update, mock_context):
    mock_context.args = ["12345"]

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = None

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "This Telegram ID is not linked to any player."
    )
