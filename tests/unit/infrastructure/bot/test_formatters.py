"""Tests for Telegram message formatters."""

from datetime import datetime

from pyball.infrastructure.telegram.formatters import build_main_keyboard, parse_callback_data


def test_build_main_keyboard_has_only_join_and_leave():
    kb = build_main_keyboard(datetime(2026, 5, 15, 20, 0))
    all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert all_data == ["join:2026-05-15T20:00", "leave:2026-05-15T20:00"]


def test_parse_callback_data_start_match_is_rejected():
    assert parse_callback_data("start_match:2026-05-15T20:00") is None


def test_parse_callback_data_rejects_unknown_action():
    assert parse_callback_data("unknown_action:2026-05-15T20:00") is None


def test_parse_callback_data_rejects_search():
    assert parse_callback_data("search:2026-05-15T20:00") is None
