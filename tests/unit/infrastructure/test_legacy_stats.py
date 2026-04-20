import pytest

from pyball.infrastructure.persistence.legacy_stats import LegacyStats


def test_get_assists_returns_correct_value():
    data = {
        "players": {
            "uuid-1": {"goals": 10, "assists": 5, "matches": 15},
            "uuid-2": {"goals": 3, "assists": 8, "matches": 20},
        }
    }
    stats = LegacyStats(data)
    assert stats.get_assists("uuid-1") == 5
    assert stats.get_assists("uuid-2") == 8
    assert stats.get_assists("unknown") == 0


def test_get_goals_returns_correct_value():
    data = {"players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}}
    stats = LegacyStats(data)
    assert stats.get_goals("uuid-1") == 10
    assert stats.get_goals("unknown") == 0


def test_get_matches_returns_correct_value():
    data = {"players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}}
    stats = LegacyStats(data)
    assert stats.get_matches("uuid-1") == 15
    assert stats.get_matches("unknown") == 0


def test_get_returns_full_dict():
    data = {"players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}}
    stats = LegacyStats(data)
    assert stats.get("uuid-1") == {"goals": 10, "assists": 5, "matches": 15}
    assert stats.get("unknown") == {"goals": 0, "assists": 0, "matches": 0}


def test_all_players_returns_list():
    data = {
        "players": {
            "uuid-1": {"goals": 10, "assists": 5, "matches": 15},
            "uuid-2": {"goals": 3, "assists": 8, "matches": 20},
        }
    }
    stats = LegacyStats(data)
    assert sorted(stats.all_players()) == ["uuid-1", "uuid-2"]


def test_from_file_loads_valid_json(tmp_path):
    json_file = tmp_path / "legacy.json"
    json_file.write_text('{"players": {"uuid-1": {"goals": 10, "assists": 5, "matches": 15}}}')

    stats = LegacyStats.from_file(str(json_file))

    assert stats.get_goals("uuid-1") == 10
    assert stats.get_assists("uuid-1") == 5
    assert stats.get_matches("uuid-1") == 15


def test_from_file_returns_empty_for_nonexistent_file(tmp_path):
    stats = LegacyStats.from_file(str(tmp_path / "nonexistent.json"))

    assert stats.get_goals("any") == 0
    assert stats.get_assists("any") == 0
    assert stats.get_matches("any") == 0
    assert stats.all_players() == []
