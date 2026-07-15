"""Tests for Telegram message formatters."""

from datetime import datetime

from pyball.infrastructure.telegram.formatters import build_main_keyboard, parse_callback_data


def test_build_main_keyboard_without_teams_has_two_rows():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=False)
    assert len(kb.inline_keyboard) == 2


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


def test_build_main_keyboard_with_teams_has_one_row():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0), has_teams=True)
    assert len(kb.inline_keyboard) == 1


def test_build_main_keyboard_default_no_teams():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0))
    assert len(kb.inline_keyboard) == 2


def test_parse_callback_data_start_match_is_rejected():
    assert parse_callback_data("start_match:2026-05-15T20:00") is None


def test_parse_callback_data_rejects_unknown_action():
    assert parse_callback_data("unknown_action:2026-05-15T20:00") is None


def test_parse_callback_data_search():
    assert parse_callback_data("search:2026-05-15T20:00") == ("search", "2026-05-15T20:00")
