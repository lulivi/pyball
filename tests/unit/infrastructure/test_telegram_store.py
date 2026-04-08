import tempfile

from pathlib import Path

import pytest

from pyball.infrastructure.telegram_store import MessageTracking, TelegramMessageStore


def test_save_and_get_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")
        tracking = MessageTracking(chat_id=123, thread_id="456", message_id=789)

        store.save_message("2024-01-15T20:00", "main", tracking)
        result = store.get_message("2024-01-15T20:00", "main")

        assert result is not None
        assert result.chat_id == 123
        assert result.message_id == 789
