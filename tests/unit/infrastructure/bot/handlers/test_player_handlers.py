from unittest.mock import MagicMock

import pytest
from telegram.constants import ReactionEmoji

from pyball.domain.player.errors import NameAlreadyTakenError, PlayerAlreadyExistsError
from pyball.infrastructure.telegram.bot.handlers.player import (
    change_group_handler,
    change_position_handler,
    delete_player_handler,
    link_player_handler,
    list_players_handler,
    new_player_handler,
    rename_player_handler,
    unlink_player_handler,
)


@pytest.mark.asyncio
async def test_new_player_handler_success(mock_update, mock_context):
    mock_context.args = ["Luis,", "regular"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    container.create_player().execute.return_value = mock_player
    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_new_player_handler_duplicate_raises(mock_update, mock_context):
    mock_context.args = ["Luis,", "regular"]

    container = MagicMock()
    container.create_player().execute.side_effect = PlayerAlreadyExistsError(
        "Player already exists"
    )

    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "ya existe" in text.lower()


@pytest.mark.asyncio
async def test_rename_player_handler_success(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis Pérez"
    mock_player.id = player_id

    mock_context.args = ["Luis", "Pérez,", "New", "Name"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    container.rename_player().execute.return_value = None
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    container.rename_player().execute.assert_called_once_with(str(player_id.value), "New Name")
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_rename_player_handler_missing_comma_shows_usage(mock_update, mock_context):
    mock_context.args = ["Luis", "New", "Name"]

    container = MagicMock()
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "Usage" in text
    container.rename_player.assert_not_called()


@pytest.mark.asyncio
async def test_delete_player_handler_success(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "David Quesada"
    mock_player.id = player_id

    mock_context.args = ["David", "Quesada"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    await delete_player_handler(mock_update, mock_context)

    container.delete_player().execute.assert_called_once_with(str(player_id.value))
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_delete_player_handler_name_not_found(mock_update, mock_context):
    mock_context.args = ["Fantasma"]

    container = MagicMock()
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container

    await delete_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "No se encontró ningún jugador con ese nombre."
    )


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
    mock_context.args = ["Luis,", "substitute"]

    container = MagicMock()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    container.change_player_group().execute.return_value = mock_player
    container.player_repository.find_all.return_value = [mock_player]

    from pyball.domain.player.models import PlayerId

    mock_player.player_id = PlayerId.generate()
    mock_context.bot_data["container"] = container

    await change_group_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


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
async def test_new_player_handler_invalid_group(mock_update, mock_context):
    mock_context.args = ["Luis,", "vip"]
    mock_context.bot_data["container"] = MagicMock()

    await new_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        text=r"El grupo debe ser \`regular\` o \`substitute\`\.", parse_mode="MarkdownV2"
    )


@pytest.mark.asyncio
async def test_rename_player_handler_name_taken(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    mock_context.args = ["Luis,", "Existing", "Name"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    container.rename_player.return_value.execute.side_effect = NameAlreadyTakenError("name taken")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "ya está en uso" in text.lower()


@pytest.mark.asyncio
async def test_rename_player_handler_name_not_found(mock_update, mock_context):
    mock_context.args = ["NoExiste,", "New", "Name"]

    container = MagicMock()
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "No se encontró ningún jugador con ese nombre."
    )


@pytest.mark.asyncio
async def test_rename_player_handler_fuzzy_match(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    mock_context.args = ["lui,", "Carlos"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    container.rename_player().execute.return_value = None
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    container.rename_player().execute.assert_called_once_with(str(player_id.value), "Carlos")
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


@pytest.mark.asyncio
async def test_new_player_handler_multiword_name(mock_update, mock_context):
    mock_context.args = ["David", "Quesada,", "regular"]

    container = MagicMock()
    container.create_player().execute.return_value = MagicMock()
    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    container.create_player().execute.assert_called_with("David Quesada", "regular", None)


@pytest.mark.asyncio
async def test_new_player_handler_missing_comma_shows_usage(mock_update, mock_context):
    mock_context.args = ["David", "regular"]
    mock_context.bot_data["container"] = MagicMock()

    await new_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "Usage" in text


@pytest.mark.asyncio
async def test_new_player_handler_with_position(mock_update, mock_context):
    mock_context.args = ["Iker,", "regular,", "portero"]

    container = MagicMock()
    container.create_player().execute.return_value = MagicMock()
    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    container.create_player().execute.assert_called_with("Iker", "regular", "portero")


@pytest.mark.asyncio
async def test_new_player_handler_without_position_passes_none(mock_update, mock_context):
    mock_context.args = ["Luis,", "regular"]

    container = MagicMock()
    container.create_player().execute.return_value = MagicMock()
    mock_context.bot_data["container"] = container

    await new_player_handler(mock_update, mock_context)

    container.create_player().execute.assert_called_with("Luis", "regular", None)


@pytest.mark.asyncio
async def test_new_player_handler_invalid_position(mock_update, mock_context):
    mock_context.args = ["Luis,", "regular,", "lateral"]
    mock_context.bot_data["container"] = MagicMock()

    await new_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "posición" in text.lower()


@pytest.mark.asyncio
async def test_change_position_handler_success(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    mock_context.args = ["Luis,", "portero"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    await change_position_handler(mock_update, mock_context)

    container.set_player_position().execute.assert_called_once_with(
        str(player_id.value), "portero"
    )
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_change_position_handler_ninguna_sets_none(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.id = player_id

    mock_context.args = ["Luis,", "ninguna"]

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    await change_position_handler(mock_update, mock_context)

    container.set_player_position().execute.assert_called_once_with(str(player_id.value), None)


@pytest.mark.asyncio
async def test_change_position_handler_invalid_position(mock_update, mock_context):
    mock_context.args = ["Luis,", "lateral"]
    mock_context.bot_data["container"] = MagicMock()

    await change_position_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "posición" in text.lower()


@pytest.mark.asyncio
async def test_list_players_handler_shows_position(mock_update, mock_context):
    container = MagicMock()
    mock_player1 = MagicMock()
    mock_player1.name = "Iker"
    mock_player1.group = "regular"
    mock_player1.position = "portero"
    mock_player2 = MagicMock()
    mock_player2.name = "Pedro"
    mock_player2.group = "substitute"
    mock_player2.position = None

    container.player_repository.find_all.return_value = [mock_player1, mock_player2]
    mock_context.bot_data["container"] = container

    await list_players_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "Iker" in text and "portero" in text.lower()
    assert r"- `Pedro`" in text
