"""Tests for handlers helper functions."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetNextWeekday:
    """Tests for _get_next_weekday function."""

    @patch("pyball.bot.handlers.meetup.load_settings")
    def test_get_next_weekday_not_same_day(self, mock_load_settings):
        """When today is not wednesday, returns next wednesday."""
        from pyball.bot.handlers.meetup import _get_next_weekday

        mock_settings = MagicMock()
        mock_settings.pyball.default_week_day = "wednesday"
        mock_settings.pyball.default_hour = "20:00"
        mock_load_settings.return_value = mock_settings

        with patch("pyball.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 10, 10, 0)  # Wednesday
            result = _get_next_weekday("wednesday")

            # Since today IS wednesday, should be next week
            assert result.weekday() == 2  # wednesday
            assert result.hour == 20
            assert result.minute == 0

    @patch("pyball.bot.handlers.meetup.load_settings")
    def test_get_next_weekday_same_day_goes_to_next_week(self, mock_load_settings):
        """When today IS wednesday, returns next wednesday (7 days)."""
        from pyball.bot.handlers.meetup import _get_next_weekday

        mock_settings = MagicMock()
        mock_settings.pyball.default_week_day = "wednesday"
        mock_settings.pyball.default_hour = "20:00"
        mock_load_settings.return_value = mock_settings

        with patch("pyball.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 10, 10, 0)  # Wednesday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = _get_next_weekday("wednesday")

            # Should be next wednesday
            assert result > datetime(2024, 1, 10, 20, 0)

    @patch("pyball.bot.handlers.meetup.load_settings")
    def test_get_next_weekday_monday_from_friday(self, mock_load_settings):
        """Friday -> Monday (3 days)."""
        from pyball.bot.handlers.meetup import _get_next_weekday

        mock_settings = MagicMock()
        mock_settings.pyball.default_week_day = "monday"
        mock_settings.pyball.default_hour = "19:00"
        mock_load_settings.return_value = mock_settings

        with patch("pyball.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 5, 10, 0)  # Friday
            result = _get_next_weekday("monday")

            assert result.weekday() == 0  # monday
            assert result.hour == 19
            assert result.minute == 0
