"""Tests for TelegramMessageStore."""

import pytest

from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore


@pytest.fixture
def message_store(tmp_path):
    """Return a TelegramMessageStore backed by a temp file."""
    return TelegramMessageStore(tmp_path / "messages.json")


def test_save_and_get_message(message_store):
    tracking = MessageTracking(chat_id=123, thread_id="456", message_id=789)

    message_store.save_message("2024-01-15T20:00", "regular", tracking)
    result = message_store.get_message("2024-01-15T20:00", "regular")

    assert result is not None
    assert result.chat_id == 123
    assert result.message_id == 789


def test_save_substitute_message(message_store):
    tracking = MessageTracking(chat_id=456, thread_id=None, message_id=111)

    message_store.save_message("2024-01-15T20:00", "substitute", tracking)
    result = message_store.get_message("2024-01-15T20:00", "substitute")

    assert result is not None
    assert result.chat_id == 456
    assert result.message_id == 111


def test_get_message_not_found(message_store):
    result = message_store.get_message("2024-01-15T20:00", "regular")

    assert result is None


def test_delete_message(message_store):
    tracking = MessageTracking(chat_id=123, thread_id=None, message_id=789)

    message_store.save_message("2024-01-15T20:00", "regular", tracking)
    message_store.delete_message("2024-01-15T20:00", "regular")

    result = message_store.get_message("2024-01-15T20:00", "regular")
    assert result is None
