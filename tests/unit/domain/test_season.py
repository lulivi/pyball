"""Tests for the season-boundary pure domain helper."""

from datetime import date

from pyball.domain.meetup.season import _season_start


class TestSeasonStart:
    """Direct tests for the Sep 1 season-boundary helper."""

    def test_september_onwards_starts_this_years_season(self):
        """From September to December the season year is the current year."""
        assert _season_start(date(2026, 9, 1)) == date(2026, 9, 1)
        assert _season_start(date(2026, 12, 31)) == date(2026, 9, 1)

    def test_before_september_uses_last_years_season(self):
        """From January to August the season started on Sep 1 of the previous year."""
        assert _season_start(date(2026, 8, 31)) == date(2025, 9, 1)
        assert _season_start(date(2026, 1, 15)) == date(2025, 9, 1)
        assert _season_start(date(2024, 2, 29)) == date(2023, 9, 1)
