from datetime import datetime

import pytest

from pyball.infrastructure.persistence.legacy_stats import LegacyStats

_DATA = {
    "players": {
        "uuid-1": {
            "assists_by_match": [
                {"date": "2023-01-01T10:00:00", "count": 2},
                {"date": "2023-02-01T10:00:00", "count": 3},
            ]
        },
        "uuid-2": {
            "assists_by_match": [
                {"date": "2023-01-01T10:00:00", "count": 8},
            ]
        },
    }
}


def test_get_assists_returns_total_all_time():
    stats = LegacyStats(_DATA)
    assert stats.get_assists("uuid-1") == 5
    assert stats.get_assists("uuid-2") == 8
    assert stats.get_assists("unknown") == 0


def test_get_assists_since_filters_by_date():
    stats = LegacyStats(_DATA)
    assert stats.get_assists("uuid-1", datetime(2023, 2, 1)) == 3
    assert stats.get_assists("uuid-1", datetime(2023, 3, 1)) == 0


def test_all_players_returns_list():
    stats = LegacyStats(_DATA)
    assert sorted(stats.all_players()) == ["uuid-1", "uuid-2"]


def test_from_file_loads_valid_json(tmp_path):
    json_file = tmp_path / "legacy.json"
    json_file.write_text(
        '{"players": {"uuid-1": {"assists_by_match":'
        ' [{"date": "2023-01-01T10:00:00", "count": 5}]}}}'
    )
    stats = LegacyStats.from_file(str(json_file))
    assert stats.get_assists("uuid-1") == 5


def test_from_file_returns_empty_for_nonexistent_file(tmp_path):
    stats = LegacyStats.from_file(str(tmp_path / "nonexistent.json"))
    assert stats.get_assists("any") == 0
    assert stats.all_players() == []
