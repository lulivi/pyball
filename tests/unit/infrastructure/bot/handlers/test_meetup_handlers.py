"""Tests for meetup bot handlers."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode, ReactionEmoji

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupAlreadyClosedError,
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    UnknownAlgorithmError,
)
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.telegram.bot.handlers.meetup import (
    _date_usage_msg,
    add_player_handler,
    close_triangular_handler,
    create_teams_handler,
    lock_handler,
    new_meetup_handler,
    next_meetup_handler,
    remove_player_handler,
    search_handler,
    show_meetup_handler,
    stats_handler,
    unlock_handler,
)


@pytest.mark.asyncio
async def test_lock_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """lock with no args calls refresh with locked=True on the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)

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
        locked=True,
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
async def test_new_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/meetup_new`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_new_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["not-a-date", "20:00"]

    await new_meetup_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert r"Formato de fecha no válido\." in text
    assert "Formato: `%Y-%m-%d %H:%M`" in text
    assert "Ejemplo: `/meetup_new`" in text
    assert call.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_show_meetup_handler_no_args_uses_active_meetup(mock_update, mock_context):
    """show_meetup with no args displays the active meetup."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 4, 20, 0)
    meetup.players = []
    meetup.teams = None

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
    assert "Ejemplo: `/meetup_show`" in text
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
        msg = _date_usage_msg("meetup_new", fmt)
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/meetup_new` `2026-05-01 14:30`"
    )


def test_date_usage_msg_with_suffix():
    fmt = "%Y-%m-%d %H:%M"
    fixed = datetime(2026, 5, 1, 14, 30)
    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        msg = _date_usage_msg("meetup_add_player", fmt, r"`<name1>`, `<name2>`, \.\.\.")
    assert msg == (
        r"Formato de fecha no válido\."
        "\n"
        "Formato: `%Y-%m-%d %H:%M`"
        "\n"
        r"Ejemplo: `/meetup_add_player` `2026-05-01 14:30` `<name1>`, `<name2>`, \.\.\."
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
async def test_create_teams_handler_with_team_count_three(mock_update, mock_context):
    """/meetup_create_teams <fecha> <hora> balanceado 3 passes team_count=3 through."""
    container = MagicMock()
    meetup = MagicMock()
    meetup.teams = [MagicMock(), MagicMock(), MagicMock()]
    container.create_teams.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "balanceado", "3"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await create_teams_handler(mock_update, mock_context)

    container.create_teams.return_value.execute.assert_called_once()
    call_args = container.create_teams.return_value.execute.call_args
    assert call_args.args[1] == 3
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_create_teams_handler_defaults_to_team_count_two(mock_update, mock_context):
    """Without a trailing count, team_count defaults to 2 (unchanged behavior)."""
    container = MagicMock()
    meetup = MagicMock()
    meetup.teams = [MagicMock(), MagicMock()]
    container.create_teams.return_value.execute.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "balanceado"]

    with patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"):
        await create_teams_handler(mock_update, mock_context)

    container.create_teams.return_value.execute.assert_called_once()
    call_args = container.create_teams.return_value.execute.call_args
    assert call_args.args[1] == 2


@pytest.mark.asyncio
async def test_create_teams_handler_invalid_team_count_non_numeric(mock_update, mock_context):
    """A non-numeric trailing team-count arg shows the usage message and doesn't execute."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "balanceado", "abc"]

    await create_teams_handler(mock_update, mock_context)

    container.create_teams.return_value.execute.assert_not_called()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "Formato de fecha no válido" in text


@pytest.mark.asyncio
async def test_create_teams_handler_invalid_team_count_out_of_range(mock_update, mock_context):
    """A trailing team-count arg outside {2, 3} shows the usage message and doesn't execute."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-05-06", "20:00", "balanceado", "4"]

    await create_teams_handler(mock_update, mock_context)

    container.create_teams.return_value.execute.assert_not_called()
    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "Formato de fecha no válido" in text


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


@pytest.mark.asyncio
async def test_change_date_2args_changes_active_meetup_date(mock_update, mock_context):
    """change_date with 2 args moves the active meetup to the given date."""
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_date_handler
    from pyball.infrastructure.telegram.message_store import TelegramMessageStore

    old_date = datetime(2026, 6, 8, 20, 0)
    new_date = datetime(2026, 6, 15, 20, 0)

    meetup = MagicMock()
    meetup.date = old_date

    updated = MagicMock()
    updated.date = new_date

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.update_meetup_date.return_value.execute.return_value = updated
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-06-15", "20:00"]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
    ) as mock_refresh, patch.object(TelegramMessageStore, "rename_date") as mock_rename:
        mock_refresh.return_value = None
        await change_date_handler(mock_update, mock_context)

    container.update_meetup_date.return_value.execute.assert_called_once_with(old_date, new_date)
    mock_rename.assert_called_once_with(old_date, new_date)
    mock_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_date_4args_changes_specific_meetup(mock_update, mock_context):
    """change_date with 4 args selects meetup by first pair, moves to second pair."""
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_date_handler
    from pyball.infrastructure.telegram.message_store import TelegramMessageStore

    old_date = datetime(2026, 6, 8, 20, 0)
    new_date = datetime(2026, 6, 15, 20, 0)

    updated = MagicMock()
    updated.date = new_date

    container = MagicMock()
    container.update_meetup_date.return_value.execute.return_value = updated
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-06-08", "20:00", "2026-06-15", "20:00"]

    with patch(
        "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
    ) as mock_refresh, patch.object(TelegramMessageStore, "rename_date") as mock_rename:
        mock_refresh.return_value = None
        await change_date_handler(mock_update, mock_context)

    container.update_meetup_date.return_value.execute.assert_called_once_with(old_date, new_date)
    mock_rename.assert_called_once_with(old_date, new_date)


@pytest.mark.asyncio
async def test_change_date_wrong_arg_count_replies_usage(mock_update, mock_context):
    """change_date with 1 or 3 args replies with a usage message."""
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_date_handler

    mock_context.args = ["2026-06-08"]

    await change_date_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_triangular_handler_closes_and_sends_summary(
    mock_update, mock_context, monkeypatch
):
    """/meetup_close_triangular closes the meetup and sends the final round summary.

    It also mirrors the classic-close cleanup: the callup keyboard is locked,
    tracked messages are dropped, and season stats are posted.
    """
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)
    closed_meetup = MagicMock()

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.close_meetup.return_value.execute.return_value = closed_meetup
    container.player_repository.find_all.return_value = []
    container.format_match_summary.return_value.execute.return_value = "resumen final"
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.regulars.chat_id = -1009999
    mock_context.bot_data["settings"].telegram.regulars.meetups_thread_id = "42"
    mock_context.args = []

    stats_calls = []

    async def _fake_post_match_stats(bot, container_arg, settings_arg):
        stats_calls.append((bot, container_arg, settings_arg))

    monkeypatch.setattr(
        "pyball.infrastructure.telegram.bot.handlers.meetup._post_match_stats",
        _fake_post_match_stats,
    )

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"
        ) as mock_refresh,
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"
        ) as mock_store_cls,
    ):
        mock_refresh.return_value = None
        await close_triangular_handler(mock_update, mock_context)
        await asyncio.sleep(0)  # let the fire-and-forget stats task run

    container.close_meetup.return_value.execute.assert_called_once_with(meetup.date)
    container.format_match_summary.return_value.execute.assert_called_once()
    mock_context.bot.send_message.assert_called_once_with(
        chat_id=-1009999,
        text="resumen final",
        message_thread_id=42,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    mock_refresh.assert_awaited_once_with(
        mock_context.bot,
        mock_context.bot_data["settings"],
        container,
        closed_meetup,
        include_keyboard=False,
    )
    mock_store_cls.return_value.delete_message.assert_any_call(closed_meetup.date, "regular")
    mock_store_cls.return_value.delete_message.assert_any_call(closed_meetup.date, "substitute")
    assert stats_calls == [(mock_context.bot, container, mock_context.bot_data["settings"])]
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_close_triangular_handler_escapes_summary_for_markdown_v2(
    mock_update, mock_context, monkeypatch
):
    """The plain-text summary is escaped for MarkdownV2 before being sent."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)
    closed_meetup = MagicMock()

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.close_meetup.return_value.execute.return_value = closed_meetup
    container.player_repository.find_all.return_value = []
    container.format_match_summary.return_value.execute.return_value = (
        "⚪ *Blanco - 2*\nNacho (Luvo)"
    )
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.regulars.chat_id = -1009999
    mock_context.bot_data["settings"].telegram.regulars.meetups_thread_id = ""
    mock_context.args = []

    monkeypatch.setattr(
        "pyball.infrastructure.telegram.bot.handlers.meetup._post_match_stats",
        AsyncMock(),
    )

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await close_triangular_handler(mock_update, mock_context)
        await asyncio.sleep(0)

    sent_text = mock_context.bot.send_message.call_args.kwargs["text"]
    assert sent_text == "⚪ *Blanco \\- 2*\nNacho \\(Luvo\\)"


@pytest.mark.asyncio
async def test_close_triangular_handler_no_matches_skips_summary_still_confirms(
    mock_update, mock_context, monkeypatch
):
    """Closing a triangular with zero played rounds doesn't crash and still confirms.

    CloseMeetup.execute() pops any dangling pending match, so a triangular where
    teams were formed but no round was ever finished ends up with no matches at
    all. FormatMatchSummary.execute() would raise ValueError("Meetup has no
    matches yet") for that meetup — the handler must skip building the summary
    instead of letting that propagate, while still confirming the close.
    """
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)
    closed_meetup = MagicMock()
    closed_meetup.matches = []

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.close_meetup.return_value.execute.return_value = closed_meetup
    mock_context.bot_data["container"] = container
    mock_context.args = []

    async def _fake_post_match_stats(bot, container_arg, settings_arg):
        del bot, container_arg, settings_arg

    monkeypatch.setattr(
        "pyball.infrastructure.telegram.bot.handlers.meetup._post_match_stats",
        _fake_post_match_stats,
    )

    with (
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.refresh_callup_messages"),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await close_triangular_handler(mock_update, mock_context)
        await asyncio.sleep(0)  # let the fire-and-forget stats task run

    container.format_match_summary.return_value.execute.assert_not_called()
    mock_context.bot.send_message.assert_not_called()
    mock_context.bot.set_message_reaction.assert_called_once_with(
        chat_id=mock_update.message.chat_id,
        message_id=mock_update.message.message_id,
        reaction=ReactionEmoji.OK_HAND_SIGN,
    )
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_close_triangular_handler_reports_already_closed(mock_update, mock_context):
    """Replies with a Spanish error when the meetup is already closed."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.close_meetup.return_value.execute.side_effect = MeetupAlreadyClosedError("x")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await close_triangular_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "ya está cerrado" in text.lower()
    mock_context.bot.send_message.assert_not_called()
    mock_context.bot.set_message_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_close_triangular_handler_reports_not_found(mock_update, mock_context):
    """Replies with a Spanish error when there's no meetup for the resolved date."""
    mock_context.args = ["2026-06-08", "20:00"]
    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = MagicMock(
        date=datetime(2026, 6, 8, 20, 0)
    )
    container.close_meetup.return_value.execute.side_effect = MeetupNotFoundError("x")
    mock_context.bot_data["container"] = container

    await close_triangular_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "No existe ningún meetup para esa fecha."
    )
    mock_context.bot.send_message.assert_not_called()
    mock_context.bot.set_message_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_close_triangular_handler_no_active_meetup_replies_error(mock_update, mock_context):
    """/meetup_close_triangular with no args and no active meetup replies in Spanish."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    await close_triangular_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()
    container.close_meetup.return_value.execute.assert_not_called()


@pytest.mark.asyncio
async def test_change_date_conflict_replies_error(mock_update, mock_context):
    """change_date replies an error message when new date is already taken."""
    from pyball.domain.meetup.errors import DuplicateMeetupError
    from pyball.infrastructure.telegram.bot.handlers.meetup import change_date_handler
    from pyball.infrastructure.telegram.message_store import TelegramMessageStore

    meetup = MagicMock()
    meetup.date = datetime(2026, 6, 8, 20, 0)

    container = MagicMock()
    container.get_active_meetup.return_value.execute.return_value = meetup
    container.update_meetup_date.return_value.execute.side_effect = DuplicateMeetupError(
        "conflict"
    )
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026-06-15", "20:00"]

    with patch.object(TelegramMessageStore, "rename_date"):
        await change_date_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "fecha" in text.lower() or "meetup" in text.lower()
