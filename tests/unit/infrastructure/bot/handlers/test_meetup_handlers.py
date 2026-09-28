"""Tests for meetup bot handlers."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode, ReactionEmoji

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.infrastructure.telegram.bot.handlers.meetup import (
    _date_usage_msg,
    _do_search,
    search_handler,
    stats_handler,
)
from pyball.infrastructure.telegram.message_store import MessageTracking


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
async def test_do_search_sends_message_and_tracks_it(mock_context):
    """_do_search sends the substitutes message and stores tracking info."""
    meetup = MagicMock()
    meetup.date = datetime(2026, 4, 25, 20, 0)
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.substitutes.meetups.chat_id = -1001234567
    settings.telegram.substitutes.meetups.message_thread_id = None
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=7))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.build_subs_keyboard",
            return_value=None,
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"
        ) as mock_store_cls,
    ):
        await _do_search(meetup, container, bot, settings, 12)

    bot.send_message.assert_called_once_with(
        chat_id=-1001234567,
        text="msg",
        reply_markup=None,
        message_thread_id=None,
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    mock_store_cls.return_value.save_message.assert_called_once()
    assert mock_store_cls.return_value.save_message.call_args.args[2].search_target == 12


@pytest.mark.asyncio
async def test_do_search_omits_keyboard_when_signup_closed(mock_context):
    """_do_search sends no keyboard once teams already exist (defensive; callers already guard)."""
    from pyball.domain.meetup.models import Meetup, PlayerId, Team

    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    pid = PlayerId.generate()
    meetup.add_player(pid)
    meetup.set_teams([Team.create("A", [pid]), Team.create("B", [])])
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.substitutes.meetups.chat_id = -1001234567
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=7))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await _do_search(meetup, container, bot, settings, 10)

    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_do_search_omits_keyboard_when_search_closed(mock_context):
    """A repost of a closed search carries no join/leave buttons."""
    from pyball.domain.meetup.models import Meetup

    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.substitutes.meetups.chat_id = -1001234567
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=7))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_subs_message",
            return_value="msg",
        ),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        await _do_search(meetup, container, bot, settings, None)

    assert bot.send_message.call_args.kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_show_regulars_message_sends_and_tracks_with_keyboard(mock_context):
    """_show_regulars_message sends to the regulars chat with a keyboard when signup is open."""
    from pyball.domain.meetup.models import Meetup

    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.regulars.meetups.chat_id = -1009876543
    settings.telegram.regulars.meetups.message_thread_id = None
    settings.pyball.team_colors = ("blanco", "negro")
    settings.pyball.team_emojis = ("⚪", "⚫")
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=9))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_main_message",
            return_value="msg",
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"
        ) as mock_store_cls,
    ):
        from pyball.infrastructure.telegram.bot.handlers.meetup import _show_regulars_message

        await _show_regulars_message(meetup, container, bot, settings)

    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == -1009876543
    assert call_kwargs["reply_markup"] is not None
    mock_store_cls.return_value.save_message.assert_called_once()


@pytest.mark.asyncio
async def test_show_regulars_message_omits_keyboard_when_signup_closed(mock_context):
    """_show_regulars_message sends no keyboard once teams already exist."""
    from pyball.domain.meetup.models import Meetup, PlayerId, Team

    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    pid = PlayerId.generate()
    meetup.add_player(pid)
    meetup.set_teams([Team.create("A", [pid]), Team.create("B", [])])
    container = MagicMock()
    container.player_repository.find_all.return_value = []
    settings = mock_context.bot_data["settings"]
    settings.telegram.regulars.meetups.chat_id = -1009876543
    settings.telegram.regulars.meetups.message_thread_id = None
    settings.pyball.team_colors = ("blanco", "negro")
    settings.pyball.team_emojis = ("⚪", "⚫")
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=9))

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.format_main_message",
            return_value="msg",
        ),
        patch("pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"),
    ):
        from pyball.infrastructure.telegram.bot.handlers.meetup import _show_regulars_message

        await _show_regulars_message(meetup, container, bot, settings)

    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["reply_markup"] is None


@pytest.mark.asyncio
async def test_show_handler_posts_to_both_chats_when_substitutes_present(
    mock_update, mock_context
):
    """show_handler posts the regulars message and, since a substitute is in the roster,
    also the substitutes message."""
    from pyball.domain.meetup.models import Meetup, PlayerId
    from pyball.domain.player.models import Player

    reg_id, sub_id = PlayerId.generate(), PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(reg_id)
    meetup.add_player(sub_id)

    regular = Player(id=reg_id, name="Reg", group="regular")
    substitute = Player(id=sub_id, name="Sub", group="substitute")

    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = meetup
    container.player_repository.find_all.return_value = [regular, substitute]
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -100
    mock_context.args = ["2026-04-25", "20:00"]

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._show_regulars_message",
            new=AsyncMock(),
        ) as mock_show_regulars,
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._do_search", new=AsyncMock()
        ) as mock_do_search,
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup.TelegramMessageStore"
        ) as mock_store_cls,
    ):
        mock_store_cls.return_value.get_message.return_value = MessageTracking(
            chat_id=-100, message_id=1, search_target=12
        )
        from pyball.infrastructure.telegram.bot.handlers.meetup import show_handler

        await show_handler(mock_update, mock_context)

    mock_show_regulars.assert_called_once_with(
        meetup, container, mock_context.bot, mock_context.bot_data["settings"]
    )
    mock_do_search.assert_called_once_with(
        meetup, container, mock_context.bot, mock_context.bot_data["settings"], 12
    )
    mock_context.bot.set_message_reaction.assert_called_once()


@pytest.mark.asyncio
async def test_show_handler_skips_substitutes_message_when_none_in_roster(
    mock_update, mock_context
):
    """show_handler skips the substitutes message entirely when no substitute is in the roster."""
    from pyball.domain.meetup.models import Meetup, PlayerId
    from pyball.domain.player.models import Player

    reg_id = PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(reg_id)

    regular = Player(id=reg_id, name="Reg", group="regular")

    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = meetup
    container.player_repository.find_all.return_value = [regular]
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -100
    mock_context.args = ["2026-04-25", "20:00"]

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._show_regulars_message",
            new=AsyncMock(),
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._do_search", new=AsyncMock()
        ) as mock_do_search,
    ):
        from pyball.infrastructure.telegram.bot.handlers.meetup import show_handler

        await show_handler(mock_update, mock_context)

    mock_do_search.assert_not_called()


@pytest.mark.asyncio
async def test_show_handler_skips_substitutes_message_when_chat_not_configured(
    mock_update, mock_context
):
    """show_handler skips the substitutes message when no substitutes chat is configured,
    even if there are substitutes in the roster."""
    from pyball.domain.meetup.models import Meetup, PlayerId
    from pyball.domain.player.models import Player

    sub_id = PlayerId.generate()
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    meetup.add_player(sub_id)

    substitute = Player(id=sub_id, name="Sub", group="substitute")

    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = meetup
    container.player_repository.find_all.return_value = [substitute]
    mock_context.bot_data["container"] = container
    from pyball.infrastructure.telegram.settings import ChatConfig

    mock_context.bot_data["settings"].telegram.substitutes.meetups = ChatConfig()
    mock_context.args = ["2026-04-25", "20:00"]

    with (
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._show_regulars_message",
            new=AsyncMock(),
        ),
        patch(
            "pyball.infrastructure.telegram.bot.handlers.meetup._do_search", new=AsyncMock()
        ) as mock_do_search,
    ):
        from pyball.infrastructure.telegram.bot.handlers.meetup import show_handler

        await show_handler(mock_update, mock_context)

    mock_do_search.assert_not_called()


@pytest.mark.asyncio
async def test_show_handler_no_active_meetup_replies_error(mock_update, mock_context):
    """show_handler replies in Spanish when there's no active meetup and no date args given."""
    container = MagicMock()
    container.get_active_meetup.return_value.execute.side_effect = MeetupNotFoundError("active")
    mock_context.bot_data["container"] = container
    mock_context.args = []

    from pyball.infrastructure.telegram.bot.handlers.meetup import show_handler

    await show_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_search_handler_success_reacts(mock_update, mock_context):
    """search reacts ✅ and sends no reply_text on success."""
    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.date = datetime(2026, 4, 25, 20, 0)
    mock_meetup.players = []
    container.meetup_repository.find_by_datetime.return_value = mock_meetup
    container.player_repository.find_all.return_value = []
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -1001234567
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
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -100
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
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -100
    mock_context.args = []

    await search_handler(mock_update, mock_context)

    call = mock_update.message.reply_text.call_args
    text = call.args[0] if call.args else call.kwargs.get("text", "")
    assert "activo" in text.lower()


@pytest.mark.asyncio
async def test_search_handler_signup_closed_replies_error(mock_update, mock_context):
    """search replies in Spanish and sends nothing once teams already exist."""
    from pyball.domain.meetup.models import Meetup, PlayerId, Team

    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Campo")
    pid = PlayerId.generate()
    meetup.add_player(pid)
    meetup.set_teams([Team.create("A", [pid]), Team.create("B", [])])

    container = MagicMock()
    container.meetup_repository.find_by_datetime.return_value = meetup
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.substitutes.meetups.chat_id = -1001234567
    mock_context.args = ["2026-04-25", "20:00"]
    mock_context.bot.send_message = AsyncMock()

    await search_handler(mock_update, mock_context)

    mock_context.bot.send_message.assert_not_called()
    text = mock_update.message.reply_text.call_args.args[0]
    assert "equipos" in text.lower()


@pytest.mark.asyncio
async def test_stats_handler_success_reacts(mock_update, mock_context):
    """stats reacts ✅ after sending the stats photo."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    mock_context.bot_data["settings"].telegram.regulars.stats.chat_id = 0
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
async def test_stats_handler_uses_stats_topic_when_sent_from_stats_chat(mock_update, mock_context):
    """When invoked from the regulars.stats chat, the photo carries its thread id."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    tg = mock_context.bot_data["settings"].telegram
    tg.regulars.stats.chat_id = -100777
    tg.regulars.stats.message_thread_id = 55
    mock_update.message.chat_id = -100777
    mock_context.args = ["temporada"]
    mock_context.bot.send_photo = AsyncMock()

    cs_path = "pyball.infrastructure.telegram.bot.handlers.meetup.ComputeStats"
    renderer_path = "pyball.infrastructure.telegram.bot.handlers.meetup.StatsHtmlRenderer"
    with patch(cs_path) as mock_cs, patch(renderer_path) as mock_renderer:
        mock_cs.return_value.execute.return_value = MagicMock()
        mock_renderer.return_value.render = AsyncMock(return_value=b"fakepng")

        await stats_handler(mock_update, mock_context)

    assert mock_context.bot.send_photo.call_args.kwargs["message_thread_id"] == 55


@pytest.mark.asyncio
async def test_stats_handler_no_topic_when_sent_from_other_chat(mock_update, mock_context):
    """Invoked outside the regulars.stats chat, the photo carries no thread id."""
    container = MagicMock()
    mock_context.bot_data["container"] = container
    tg = mock_context.bot_data["settings"].telegram
    tg.regulars.stats.chat_id = -100777
    tg.regulars.stats.message_thread_id = 55
    mock_update.message.chat_id = -100999
    mock_context.args = ["temporada"]
    mock_context.bot.send_photo = AsyncMock()

    cs_path = "pyball.infrastructure.telegram.bot.handlers.meetup.ComputeStats"
    renderer_path = "pyball.infrastructure.telegram.bot.handlers.meetup.StatsHtmlRenderer"
    with patch(cs_path) as mock_cs, patch(renderer_path) as mock_renderer:
        mock_cs.return_value.execute.return_value = MagicMock()
        mock_renderer.return_value.render = AsyncMock(return_value=b"fakepng")

        await stats_handler(mock_update, mock_context)

    assert mock_context.bot.send_photo.call_args.kwargs["message_thread_id"] is None
