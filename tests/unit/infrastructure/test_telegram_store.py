import tempfile

from pathlib import Path

import pytest

from pyball.infrastructure.telegram_store import MessageTracking, TelegramMessageStore


def test_save_and_get_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")
        tracking = MessageTracking(chat_id=123, thread_id="456", message_id=789)

        store.save_message("2024-01-15T20:00", "regular", tracking)
        result = store.get_message("2024-01-15T20:00", "regular")

        assert result is not None
        assert result.chat_id == 123
        assert result.message_id == 789


def test_save_substitute_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")
        tracking = MessageTracking(chat_id=456, thread_id=None, message_id=111)

        store.save_message("2024-01-15T20:00", "substitute", tracking)
        result = store.get_message("2024-01-15T20:00", "substitute")

        assert result is not None
        assert result.chat_id == 456
        assert result.message_id == 111


def test_get_message_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")

        result = store.get_message("2024-01-15T20:00", "regular")

        assert result is None


def test_delete_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")
        tracking = MessageTracking(chat_id=123, thread_id=None, message_id=789)

        store.save_message("2024-01-15T20:00", "regular", tracking)
        store.delete_message("2024-01-15T20:00", "regular")

        result = store.get_message("2024-01-15T20:00", "regular")
        assert result is None
