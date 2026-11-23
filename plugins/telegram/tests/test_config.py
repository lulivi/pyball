"""Tests for the plugin's config table."""

import pytest
from pyball_client.plugin import PluginError

from pyball_telegram.config import Chat, from_table

TABLE = {
    "bot_token": "123:abc",
    "admins_ids": [1, 2],
    "regulars": {"meetups": {"chat_id": -10, "message_thread_id": 5}, "stats": {"chat_id": -30}},
    "substitutes": {"meetups": {"chat_id": -20, "message_thread_id": ""}},
}


def test_reads_the_chats_and_admins():
    """Every key of [pyball.plugins.telegram], an empty topic meaning none."""
    config = from_table(TABLE)
    assert config.admins_ids == {1, 2}
    assert config.regulars_meetups == Chat(-10, 5)
    assert config.substitutes_meetups == Chat(-20, None)
    assert config.regulars_stats == Chat(-30, None)
    assert config.mapping_file.as_posix() == "data/plugins/telegram/telegram-uuid.json"


def test_stats_chat_is_optional():
    """Without regulars.stats there is no stats chat."""
    table = TABLE | {"regulars": {"meetups": {"chat_id": -10}}}
    assert not from_table(table).regulars_stats


def test_missing_required_keys_are_listed():
    """Token, admins and both callup chats are required."""
    with pytest.raises(PluginError) as caught:
        from_table({})
    for key in ("bot_token", "admins_ids", "regulars.meetups", "substitutes.meetups"):
        assert key in str(caught.value)


def test_bad_values_are_refused():
    """A non-numeric chat id or admin is an error."""
    with pytest.raises(PluginError, match="numbers"):
        from_table(TABLE | {"substitutes": {"meetups": {"chat_id": "x"}}})
    with pytest.raises(PluginError, match="admins_ids"):
        from_table(TABLE | {"admins_ids": "1,2"})
