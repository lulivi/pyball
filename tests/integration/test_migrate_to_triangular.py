"""Tests for the one-time meetup JSON schema migration script."""

import json

from scripts.migrate_to_triangular import migrate_directory, migrate_meetup_dict


def test_migrate_meetup_dict_wraps_result_into_matches_list():
    """Test that closed meetup's result is wrapped into matches list."""
    old = {
        "id": "11111111-1111-1111-1111-111111111111",
        "date": "2026-04-12T20:00:00",
        "location": "Campo Norte",
        "players": [],
        "teams": [
            {"name": "A", "players": []},
            {"name": "B", "players": []},
        ],
        "result": {"score_a": 2, "score_b": 1, "events": []},
    }

    migrated = migrate_meetup_dict(old)

    assert migrated["matches"] == [
        {"teams_playing": ["A", "B"], "result": {"score_a": 2, "score_b": 1, "events": []}}
    ]
    assert migrated["closed"] is True
    assert "result" not in migrated


def test_migrate_meetup_dict_open_meetup_has_no_matches_and_is_not_closed():
    """Test that open meetup has no matches and is not closed."""
    old = {
        "id": "11111111-1111-1111-1111-111111111111",
        "date": "2026-04-12T20:00:00",
        "location": "Campo Norte",
        "players": [],
        "teams": None,
        "result": None,
    }

    migrated = migrate_meetup_dict(old)

    assert migrated["matches"] == []
    assert migrated["closed"] is False


def test_migrate_meetup_dict_is_idempotent_on_already_migrated_files():
    """Test that migration is idempotent on already migrated files."""
    already_migrated = {
        "id": "11111111-1111-1111-1111-111111111111",
        "date": "2026-04-12T20:00:00",
        "location": "Campo Norte",
        "players": [],
        "teams": None,
        "matches": [],
        "closed": False,
    }

    assert migrate_meetup_dict(already_migrated) == already_migrated


def test_migrate_directory_rewrites_every_json_file(tmp_path):
    """Test that migrate_directory rewrites every JSON file in place."""
    old = {
        "id": "11111111-1111-1111-1111-111111111111",
        "date": "2026-04-12T20:00:00",
        "location": "Campo Norte",
        "players": [],
        "teams": [{"name": "A", "players": []}, {"name": "B", "players": []}],
        "result": {"score_a": 1, "score_b": 0, "events": []},
    }
    meetup_file = tmp_path / "2026-04-12T20:00.json"
    meetup_file.write_text(json.dumps(old), encoding="utf-8")

    migrate_directory(tmp_path)

    rewritten = json.loads(meetup_file.read_text(encoding="utf-8"))
    assert rewritten["matches"][0]["result"]["score_a"] == 1
    assert "result" not in rewritten
