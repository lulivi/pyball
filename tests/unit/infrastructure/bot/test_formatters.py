"""Tests for Telegram message formatters."""

from datetime import datetime

from pyball.infrastructure.telegram.formatters import build_main_keyboard, parse_callback_data


def test_build_main_keyboard_without_teams_has_three_rows():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    assert len(kb.inline_keyboard) == 3


def test_build_main_keyboard_without_teams_has_create_teams_buttons():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "create_teams:2026-05-15T20:00" in all_data
    assert "create_teams_3:2026-05-15T20:00" in all_data


def test_build_main_keyboard_create_teams_button_labels():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    all_labels = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔀 Crear 2 equipos" in all_labels
    assert "🔀 Crear 3 equipos" in all_labels


def test_build_main_keyboard_without_teams_no_lock_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert not any("lock" in (d or "") for d in all_data)


def test_build_main_keyboard_without_teams_has_search_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    all_labels = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "search:2026-05-15T20:00" in all_data
    assert "🔎 Buscar jugadores" in all_labels


def test_build_main_keyboard_with_teams_no_search_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=True)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert not any("search" in (d or "") for d in all_data)


def test_build_main_keyboard_locked_no_search_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False, locked=True)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert not any("search" in (d or "") for d in all_data)


def test_build_main_keyboard_with_teams_has_three_rows():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=True)
    assert len(kb.inline_keyboard) == 3


def test_build_main_keyboard_with_teams_has_lock_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=True)
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert any("lock" in (d or "") for d in all_data)


def test_build_main_keyboard_default_no_teams():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0))
    assert len(kb.inline_keyboard) == 3


def test_build_main_keyboard_locked_has_single_unlock_button():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=True, locked=True)
    assert len(kb.inline_keyboard) == 1
    assert len(kb.inline_keyboard[0]) == 1
    btn = kb.inline_keyboard[0][0]
    assert btn.text == "🔓 Desfijar partido"
    assert btn.callback_data == "unlock:2026-05-15T20:00"


def test_parse_callback_data_create_teams():
    assert parse_callback_data("create_teams:2026-05-15T20:00") == (
        "create_teams",
        "2026-05-15T20:00",
    )


def test_parse_callback_data_create_teams_3():
    assert parse_callback_data("create_teams_3:2026-05-15T20:00") == (
        "create_teams_3",
        "2026-05-15T20:00",
    )


def test_parse_callback_data_lock():
    assert parse_callback_data("lock:2026-05-15T20:00") == ("lock", "2026-05-15T20:00")


def test_parse_callback_data_unlock():
    assert parse_callback_data("unlock:2026-05-15T20:00") == ("unlock", "2026-05-15T20:00")


def test_parse_callback_data_start_match_is_rejected():
    assert parse_callback_data("start_match:2026-05-15T20:00") is None


def test_parse_callback_data_rejects_unknown_action():
    assert parse_callback_data("unknown_action:2026-05-15T20:00") is None


def test_parse_callback_data_search():
    assert parse_callback_data("search:2026-05-15T20:00") == ("search", "2026-05-15T20:00")
