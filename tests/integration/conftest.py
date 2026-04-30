"""Shared fixtures for integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Message, Update, User
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository
from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository

# pylint: disable=redefined-outer-name


@pytest.fixture
def tmp_data(tmp_path):
    """Temp directory with meetups/ subdir pre-created."""
    (tmp_path / "meetups").mkdir()
    return tmp_path


@pytest.fixture
def real_container(tmp_data, monkeypatch):
    """Real Container with JSON repos backed by tmp_data."""
    settings_mock = MagicMock()
    settings_mock.pyball.location = "Test Field"
    settings_mock.pyball.base_url = "http://localhost:8000"
    settings_mock.paths.players_file = tmp_data / "players.json"
    settings_mock.paths.meetups_dir = tmp_data / "meetups"

    monkeypatch.setattr("pyball.application.container.load_settings", lambda: settings_mock)

    container = Container()
    # pylint: disable-next=protected-access
    container._player_repository = JsonPlayerRepository(tmp_data / "players.json")
    # pylint: disable-next=protected-access
    container._meetup_repository = JsonMeetupRepository(tmp_data / "meetups")
    # pylint: disable-next=protected-access
    container._data_dir = tmp_data  # ensures legacy_stats resolves to tmp_data path
    return container


@pytest.fixture
def bot_settings(tmp_data):
    """Build settings mock for bot_data with real temp file paths."""
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    settings.telegram.admins_ids = [99999]
    settings.telegram.regulars.chat_id = -100111
    settings.telegram.regulars.meetups_thread_id = None
    settings.telegram.substitutes.chat_id = -100222
    settings.paths.bot_messages_file = tmp_data / "bot_messages.json"
    settings.paths.bot_mappings_file = tmp_data / "bot_mappings.json"
    settings.pyball.location = "Test Field"
    settings.pyball.default_week_day = "wednesday"
    settings.pyball.default_hour = "20:00"
    return settings


@pytest.fixture
def bot_update():
    """Minimal authorized Update mock with real-enough spec."""
    update = MagicMock(spec=Update)
    message = AsyncMock(spec=Message)
    update.message = message
    user = MagicMock(spec=User)
    user.id = 12345
    update.effective_user = user
    return update


@pytest.fixture
def bot_context(real_container, bot_settings):
    """Build ContextTypes mock wired to real_container and mocked bot API."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"container": real_container, "settings": bot_settings}
    context.bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 42
    context.bot.send_message = AsyncMock(return_value=sent_msg)
    context.bot.edit_message_text = AsyncMock()
    context.bot.send_photo = AsyncMock()
    return context
