"""Tests for TelegramMessageStore."""

import json
from datetime import datetime

import pytest

from pyball.infrastructure.telegram.message_store import MessageTracking, TelegramMessageStore


@pytest.fixture
def message_store(tmp_path):
    """Return a TelegramMessageStore backed by a temp file."""
    return TelegramMessageStore(tmp_path / "messages.json")


def test_save_and_get_message(message_store):
    tracking = MessageTracking(chat_id=123, thread_id="456", message_id=789)

    message_store.save_message(datetime(2024, 1, 15, 20, 0), "regular", tracking)
    result = message_store.get_message(datetime(2024, 1, 15, 20, 0), "regular")

    assert result is not None
    assert result.chat_id == 123
    assert result.message_id == 789
    assert result.thread_id == "456"


def test_save_substitute_message(message_store):
    tracking = MessageTracking(chat_id=456, thread_id=None, message_id=111)

    message_store.save_message(datetime(2024, 1, 15, 20, 0), "substitute", tracking)
    result = message_store.get_message(datetime(2024, 1, 15, 20, 0), "substitute")

    assert result is not None
    assert result.chat_id == 456
    assert result.message_id == 111


def test_get_message_not_found(message_store):
    result = message_store.get_message(datetime(2024, 1, 15, 20, 0), "regular")

    assert result is None


def test_delete_message(message_store):
    tracking = MessageTracking(chat_id=123, thread_id=None, message_id=789)

    message_store.save_message(datetime(2024, 1, 15, 20, 0), "regular", tracking)
    message_store.delete_message(datetime(2024, 1, 15, 20, 0), "regular")

    result = message_store.get_message(datetime(2024, 1, 15, 20, 0), "regular")
    assert result is None


def test_rename_date_moves_entry_to_new_key(message_store):
    """rename_date re-keys messages from old_date to new_date."""
    old = datetime(2026, 6, 8, 20, 0)
    new = datetime(2026, 6, 15, 20, 0)
    tracking = MessageTracking(chat_id=111, thread_id=None, message_id=222)

    message_store.save_message(old, "regular", tracking)
    message_store.rename_date(old, new)

    assert message_store.get_message(old, "regular") is None
    result = message_store.get_message(new, "regular")
    assert result is not None
    assert result.message_id == 222


def test_rename_date_noop_when_old_key_absent(message_store):
    """rename_date is a no-op if the old date has no entry."""
    old = datetime(2026, 6, 8, 20, 0)
    new = datetime(2026, 6, 15, 20, 0)

    message_store.rename_date(old, new)  # must not raise

    assert message_store.get_message(new, "regular") is None
