from pathlib import Path

import pytest

from pyball.infrastructure.telegram.mapping import TelegramMappingStore


@pytest.fixture
def mapping_store(tmp_path):
    return TelegramMappingStore(tmp_path / "mapping.json")


def test_set_and_get_player_id(mapping_store):
    mapping_store.set_player_id(12345, "player1")
    assert mapping_store.get_player_id(12345) == "player1"


def test_get_nonexistent_player_id(mapping_store):
    assert mapping_store.get_player_id(99999) is None


def test_delete_player_id(mapping_store):
    mapping_store.set_player_id(12345, "player1")
    mapping_store.delete_player_id(12345)
    assert mapping_store.get_player_id(12345) is None


def test_delete_nonexistent_player_id(mapping_store):
    mapping_store.delete_player_id(99999)  # Should not raise
    assert mapping_store.get_player_id(99999) is None


def test_get_telegram_id_returns_linked_id(mapping_store):
    mapping_store.set_player_id(12345, "player1")
    assert mapping_store.get_telegram_id("player1") == 12345


def test_get_telegram_id_unlinked_returns_none(mapping_store):
    assert mapping_store.get_telegram_id("ghost") is None
