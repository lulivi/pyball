"""Tests for meetup bot handlers."""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode, ReactionEmoji

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupHasNoTeamsError,
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    UnknownAlgorithmError,
)
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram.bot.handlers.meetup import (
    _date_usage_msg,
    add_player_handler,
    create_teams_handler,
    generate_qr_bytes,
    lock_handler,
    match_qr_handler,
    new_meetup_handler,
    next_meetup_handler,
    remove_player_handler,
    search_handler,
    show_meetup_handler,
    stats_handler,
    unlock_handler,
)


def test_generate_qr_bytes_returns_png_buffer():
    buf = generate_qr_bytes("https://example.com/match?date=2026-04-19")
    assert isinstance(buf, BytesIO)
    header = buf.read(4)
    assert header == b"\x89PNG"


@pytest.mark.asyncio
async def test_lock_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """lock with no args calls refresh with include_keyboard=False on the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
    ) as mock_refresh:
        mock_refresh.return_value = None
        await lock_handler(mock_update, mock_context)

    mock_refresh.assert_awaited_once_with(
        mock_context.bot,
        mock_context.bot_data["settings"],
        container,
        meetup,
        include_keyboard=False,
    )


@pytest.mark.asyncio
async def test_lock_handler_no_active_meetup_replies_error(mock_update, mock_context):
    """lock with no active meetup sends Spanish error reply."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container

    await lock_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_unlock_handler_uses_active_meetup(mock_update, mock_context):
    """unlock calls refresh with include_keyboard=True on the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
    ) as mock_refresh:
        mock_refresh.return_value = None
        await unlock_handler(mock_update, mock_context)

    mock_refresh.assert_awaited_once_with(
        mock_context.bot,
        mock_context.bot_data["settings"],
        container,
        meetup,
    )


@pytest.mark.asyncio
async def test_match_qr_handler_sends_qr_to_admins(mock_update, mock_context):
    """match_qr sends a QR photo to each configured admin."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    url = "http://pyball:8000/match?token=secret"
    admin_id = 99999

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.start_match.return_value.execute.return_value = url
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].pyball.base_url = "http://pyball:8000"
    mock_context.bot_data["settings"].telegram.admins_ids = [admin_id]
    mock_context.bot = AsyncMock()
    mock_context.args = []

    fake_buf = BytesIO(b"fakepng")

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.generate_qr_bytes",
        return_value=fake_buf,
    ) as mock_qr:
        await match_qr_handler(mock_update, mock_context)

    mock_qr.assert_called_once_with(url)
    mock_context.bot.send_photo.assert_called_once_with(
        chat_id=admin_id,
        photo=fake_buf,
        caption=f"🔗 Enlace del partido:\n{url}",
    )


@pytest.mark.asyncio
async def test_match_qr_handler_no_base_url_replies_error(mock_update, mock_context):
    """match_qr replies error when base_url is not configured."""
    mock_context.bot_data["settings"].pyball.base_url = ""
    mock_context.bot_data["container"] = MagicMock()
    mock_context.args = []

    await match_qr_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "url" in text.lower() or "base" in text.lower()


@pytest.mark.asyncio
async def test_match_qr_handler_no_teams_replies_error(mock_update, mock_context):
    """match_qr replies in Spanish when meetup has no teams."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.start_match.return_value.execute.side_effect = MeetupHasNoTeamsError("no teams")
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].pyball.base_url = "http://pyball:8000"
    mock_context.bot_data["settings"].pyball.display_date_format = "%Y-%m-%d %H:%M"
    mock_context.args = []

    await match_qr_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "equipos" in text.lower()


@pytest.mark.asyncio
async def test_new_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/new_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/new_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """show_meetup with no args displays the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.players = []
    meetup.teams = None
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.args = []

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.format_main_message",
        return_value="mensaje",
    ) as mock_fmt:
        await show_meetup_handler(mock_update, mock_context)

    mock_fmt.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args_no_active_meetup_replies_error(
    mock_update, mock_context
):
    """show_meetup with no args replies in Spanish when no active meetup exists."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await show_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_show_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["bad", "date"]
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Ejemplo: `/show_meetup`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_not_found(mock_update, mock_context):
    mock_context.args = ["2026-04-25", "20:00"]

    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = None
    mock_context.bot_data["container"] = container

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("No existe ningún meetup para esa fecha.")


@pytest.mark.asyncio
async def test_create_teams_handler_no_teams(mock_update, mock_context):
    mock_context.args = ["2026-04-25", "20:00"]

    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.teams = []
    container.create_teams.return_value.execute.return_value = mock_meetup
    mock_context.bot_data["container"] = container

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("No se han creado equipos.")


def test_date_usage_msg_no_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("new_meetup", fmt)
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/new_meetup` `2026-05-01 14:30`"
    )


def test_date_usage_msg_with_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("add_player", fmt, r"`<name1>`, `<name2>`, \.\.\.")
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/add_player` `2026-05-01 14:30` `<name1>`, `<name2>`, \.\.\."
    )


@pytest.mark.asyncio
async def test_new_meetup_handler_duplicate_replies_spanish(mock_update, mock_context):
    """new_meetup replies in Spanish when meetup already exists for that date."""
    container = MagicMock()
    container.create_meetup.return_value.execute.side_effect = DuplicateMeetupError(
        "already exists"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00"]
    mock_context.bot_data["settings"].pyball.display_date_format = "%Y-%m-%d %H:%M"

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.kwargs.get("text") or (call.args[0] if call.args else "")
    assert "ya existe" in text.lower()


@pytest.mark.asyncio
async def test_new_meetup_handler_unexpected_error(mock_update, mock_context):
    """new_meetup logs and replies in Spanish on unexpected errors."""
    container = MagicMock()
    container.create_meetup.return_value.execute.side_effect = RuntimeError("db crash")
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.logger") as mock_logger:
        await new_meetup_handler(mock_update, mock_context)

    mock_logger.exception.assert_called_once()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "error inesperado" in text.lower()


@pytest.mark.asyncio
async def test_add_player_handler_meetup_not_found(mock_update, mock_context):
    """add_player replies in Spanish when meetup does not exist."""
    container = MagicMock()
    container.add_player_to_meetup.return_value.execute.side_effect = MeetupNotFoundError(
        "2026-04-25T20:00"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    await add_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "no existe" in text.lower() or "no se ha encontrado" in text.lower()


@pytest.mark.asyncio
async def test_add_player_handler_unexpected_error(mock_update, mock_context):
    """add_player logs and replies in Spanish on unexpected errors."""
    container = MagicMock()
    container.add_player_to_meetup.return_value.execute.side_effect = RuntimeError("crash")
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.logger") as mock_logger:
        await add_player_handler(mock_update, mock_context)

    mock_logger.exception.assert_called_once()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "error inesperado" in text.lower()


@pytest.mark.asyncio
async def test_remove_player_handler_meetup_not_found(mock_update, mock_context):
    """remove_player replies in Spanish when meetup does not exist."""
    container = MagicMock()
    container.remove_player_from_meetup.return_value.execute.side_effect = MeetupNotFoundError(
        "2026-04-25T20:00"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    await remove_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "no existe" in text.lower() or "no se ha encontrado" in text.lower()


@pytest.mark.asyncio
async def test_remove_player_handler_player_not_in_meetup(mock_update, mock_context):
    """remove_player replies in Spanish when player is not in the meetup."""
    container = MagicMock()
    container.remove_player_from_meetup.return_value.execute.side_effect = PlayerNotInMeetupError(
        "player-uuid"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    await remove_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "no está" in text.lower() or "no se encuentra" in text.lower()


@pytest.mark.asyncio
async def test_remove_player_handler_unexpected_error(mock_update, mock_context):
    """remove_player logs and replies in Spanish on unexpected errors."""
    container = MagicMock()
    container.remove_player_from_meetup.return_value.execute.side_effect = RuntimeError("crash")
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.logger") as mock_logger:
        await remove_player_handler(mock_update, mock_context)

    mock_logger.exception.assert_called_once()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "error inesperado" in text.lower()


@pytest.mark.asyncio
async def test_create_teams_handler_meetup_not_found(mock_update, mock_context):
    """create_teams replies in Spanish when meetup does not exist."""
    container = MagicMock()
    container.create_teams.return_value.execute.side_effect = MeetupNotFoundError(
        "2026-04-25T20:00"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00"]

    await create_teams_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "no existe" in text.lower() or "no se ha encontrado" in text.lower()


@pytest.mark.asyncio
async def test_create_teams_handler_unexpected_error(mock_update, mock_context):
    """create_teams logs and replies in Spanish on unexpected errors."""
    container = MagicMock()
    container.create_teams.return_value.execute.side_effect = RuntimeError("crash")
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.logger") as mock_logger:
        await create_teams_handler(mock_update, mock_context)

    mock_logger.exception.assert_called_once()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "error inesperado" in text.lower()


@pytest.mark.asyncio
async def test_create_teams_handler_passes_algo_name_to_container(mock_update, mock_context):
    """Handler passes the third argument as algo_name to container.create_teams()."""
    container = MagicMock()
    meetup = MagicMock()
    meetup.teams = [MagicMock(), MagicMock()]
    container.create_teams.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "random"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await create_teams_handler(mock_update, mock_context)

    container.create_teams.assert_called_once_with("random")
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_create_teams_handler_passes_none_when_no_algo(mock_update, mock_context):
    """Handler passes None as algo_name when no third argument is given."""
    container = MagicMock()
    meetup = MagicMock()
    meetup.teams = [MagicMock(), MagicMock()]
    container.create_teams.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00"]
    mock_context.bot = AsyncMock()

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await create_teams_handler(mock_update, mock_context)

    container.create_teams.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_create_teams_handler_replies_on_unknown_algorithm(mock_update, mock_context):
    """Handler replies with an error message when an unknown algorithm is requested."""
    container = MagicMock()
    container.create_teams.side_effect = UnknownAlgorithmError("xyz", ["balanceado", "random"])
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "xyz"]

    await create_teams_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "xyz" in text
    assert "balanceado" in text
    assert "random" in text


@pytest.mark.asyncio
async def test_create_teams_handler_manual_success(mock_update, mock_context):
    """manual branch calls create_teams_manually and reacts ✅ on success."""
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    container = MagicMock()
    container.create_teams_manually.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = [
        "2026-04-25",
        "20:00",
        "manual",
        "Juan,",
        "Pedro",
        ";",
        "Carlos,",
        "Maria",
    ]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages",
        new_callable=AsyncMock,
    ):
        await create_teams_handler(mock_update, mock_context)

    container.create_teams_manually.return_value.execute.assert_called_once()
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_create_teams_handler_manual_single_team_no_separator(mock_update, mock_context):
    """manual branch with no ';' calls use case with empty team_b_names."""
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    container = MagicMock()
    container.create_teams_manually.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "manual", "Juan,Pedro"]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages",
        new_callable=AsyncMock,
    ):
        await create_teams_handler(mock_update, mock_context)

    call_args = container.create_teams_manually.return_value.execute.call_args
    assert call_args.args[2] == []


@pytest.mark.asyncio
async def test_create_teams_handler_manual_single_team_trailing_separator(
    mock_update, mock_context
):
    """manual branch with trailing ';' calls use case with empty team_b_names."""
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    container = MagicMock()
    container.create_teams_manually.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "manual", "Juan,Pedro", ";"]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages",
        new_callable=AsyncMock,
    ):
        await create_teams_handler(mock_update, mock_context)

    call_args = container.create_teams_manually.return_value.execute.call_args
    assert call_args.args[2] == []


@pytest.mark.asyncio
async def test_create_teams_handler_manual_unknown_player(mock_update, mock_context):
    """manual branch replies with ValueError message when a name can't be resolved."""
    container = MagicMock()
    container.create_teams_manually.return_value.execute.side_effect = ValueError(
        "Jugadores no encontrados: Ghost"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "manual", "Ghost", ";", "Pedro"]

    await create_teams_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "Jugadores no encontrados" in text


@pytest.mark.asyncio
async def test_create_teams_handler_manual_meetup_not_found(mock_update, mock_context):
    """manual branch replies with not-found message when meetup absent."""
    container = MagicMock()
    container.create_teams_manually.return_value.execute.side_effect = MeetupNotFoundError(
        "2026-04-25T20:00"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "manual", "Juan", ";", "Pedro"]

    await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "No existe ningún meetup para esa fecha."
    )


@pytest.mark.asyncio
async def test_create_teams_handler_manual_unequal_sizes(mock_update, mock_context):
    """manual branch replies with ValueError message when team sizes differ."""
    container = MagicMock()
    container.create_teams_manually.return_value.execute.side_effect = ValueError(
        "Los equipos deben tener el mismo número de jugadores (1 vs 2)"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "manual", "Juan", ";", "Pedro,", "Carlos"]

    await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Los equipos deben tener el mismo número de jugadores (1 vs 2)"
    )


@pytest.mark.asyncio
async def test_new_meetup_handler_success_reacts(mock_update, mock_context):
    """new_meetup reacts ✅ and sends no reply_text on success."""
    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.date = datetime(2026, 4, 25, 20, 0)
    container.create_meetup.return_value.execute.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00"]
    mock_context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_main_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_main_keyboard",
            return_value=None,
        ),
    ):
        await new_meetup_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_next_meetup_handler_success_no_intermediate_message(mock_update, mock_context):
    """next_meetup reacts ✅ and never sends an intermediate text message."""
    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.date = datetime(2026, 4, 30, 20, 0)
    container.create_meetup.return_value.execute.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].pyball.default_week_day = "wednesday"
    mock_context.bot_data["settings"].pyball.default_hour = "20:00"
    mock_context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_main_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_main_keyboard",
            return_value=None,
        ),
    ):
        await next_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_not_called()
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_remove_player_handler_success_reacts(mock_update, mock_context):
    """remove_player reacts ✅ and sends no reply_text on success."""
    container = MagicMock()
    mock_meetup = MagicMock()
    container.remove_player_from_meetup.return_value.execute.return_value = mock_meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await remove_player_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_add_player_handler_all_succeed_reacts(mock_update, mock_context):
    """add_player reacts ✅ when all players are added successfully."""
    container = MagicMock()
    mock_meetup = MagicMock()
    container.add_player_to_meetup.return_value.execute.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await add_player_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_add_player_handler_partial_failure_replies_failures_only(mock_update, mock_context):
    """add_player replies with failure details (no 'Añadidos') when any player fails."""
    container = MagicMock()
    mock_meetup = MagicMock()
    use_case = container.add_player_to_meetup.return_value
    use_case.execute.side_effect = [mock_meetup, ValueError("no encontrado")]
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-04-25", "20:00", "Luis,", "Pedro"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await add_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "Fallidos" in text
    assert "Pedro" in text
    assert "Añadidos" not in text
    mock_context.bot.set_message_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_search_handler_success_reacts(mock_update, mock_context):
    """search reacts ✅ and sends no reply_text on success."""
    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.date = datetime(2026, 4, 25, 20, 0)
    container.meetup_repository.find_by_datetime.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -1001234567
    mock_context.args = ["2026-04-25", "20:00"]
    mock_context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=None,
        ),
    ):
        await search_handler(mock_update, mock_context)

    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_search_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """search with no args uses the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.players = []
    meetup.teams = None
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -100
    mock_context.bot = AsyncMock()
    mock_context.args = []

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=MagicMock(),
        ),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await search_handler(mock_update, mock_context)

    mock_context.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_search_handler_no_args_no_active_meetup_replies_error(mock_update, mock_context):
    """search with no args replies in Spanish when no active meetup exists."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.chat_id = -100
    mock_context.args = []

    await search_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_add_player_handler_no_date_uses_active_meetup(mock_update, mock_context):
    """add_player with only names (no date) uses the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.add_player_to_meetup.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["Juan"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await add_player_handler(mock_update, mock_context)

    container.add_player_to_meetup.return_value.execute.assert_called_once_with(
        meetup.date, "Juan"
    )


@pytest.mark.asyncio
async def test_add_player_handler_no_args_no_active_meetup_replies_error(
    mock_update, mock_context
):
    """add_player with no args replies in Spanish when no active meetup exists."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await add_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_remove_player_handler_no_date_uses_active_meetup(mock_update, mock_context):
    """remove_player with only a name (no date) uses the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.result = None

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.remove_player_from_meetup.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["Juan", "García"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await remove_player_handler(mock_update, mock_context)

    container.remove_player_from_meetup.return_value.execute.assert_called_once_with(
        meetup.date, "Juan García"
    )


@pytest.mark.asyncio
async def test_remove_player_handler_no_args_no_active_meetup_replies_error(
    mock_update, mock_context
):
    """remove_player with no args replies in Spanish when no active meetup exists."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await remove_player_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_stats_handler_success_reacts(mock_update, mock_context):
    """stats reacts ✅ after sending the stats photo."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.regulars.chat_id = 0
    mock_context.args = ["temporada"]
    mock_context.bot.send_photo = AsyncMock()

    cs_path = "pyball.infrastructure.telegram.bot.handlers.meetup.ComputeStats"
    renderer_path = "pyball.infrastructure.telegram.bot.handlers.meetup.StatsHtmlRenderer"
    with patch(cs_path) as mock_cs, patch(renderer_path) as mock_renderer:
        mock_cs.return_value.execute.return_value = MagicMock()
        mock_renderer.return_value.render = AsyncMock(return_value=b"fakepng")

        await stats_handler(mock_update, mock_context)

    mock_context.bot.send_photo.assert_called_once()
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )


@pytest.mark.asyncio
async def test_change_location_updates_location_and_refreshes(mock_update, mock_context):
    """change_location updates location and refreshes callup messages."""
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_location_handler

    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)
    meetup.result = None

    updated = MagicMock()
    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.update_meetup_location.return_value.execute.return_value = updated
    mock_context.bot_data["container"] = container
    mock_context.args = ["Parque", "Sur"]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
    ) as mock_refresh:
        mock_refresh.return_value = None
        await change_location_handler(mock_update, mock_context)

    container.update_meetup_location.return_value.execute.assert_called_once_with(
        meetup.date, "Parque Sur"
    )
    mock_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_location_no_args_replies_usage(mock_update, mock_context):
    """change_location with no location arg replies with usage message."""
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_location_handler

    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)
    meetup.result = None
    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await change_location_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_location_not_found_replies_error(mock_update, mock_context):
    """change_location replies error message when meetup is not found."""
    from pyball.domain.meetup.errors import MeetupNotFoundError
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_location_handler

    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("x")
    mock_context.bot_data["container"] = container
    mock_context.args = ["Parque", "Sur"]

    await change_location_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower() or "meetup" in text.lower()
