"""Shared fixtures for bot handler tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Message, Update, User
from telegram.ext import ContextTypes


@pytest.fixture
def mock_update():
    """Build a minimal authorized Update mock."""
    update = MagicMock(spec=Update)
    message = AsyncMock(spec=Message)
    update.message = message
    user = MagicMock(spec=User)
    user.id = 12345
    update.effective_user = user
    return update


@pytest.fixture
def mock_context():
    """Build a minimal ContextTypes mock with an authorized admin user."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    settings.pyball.display_date_format = "%Y-%m-%d %H:%M"
    context.bot_data = {"settings": settings}
    return context
