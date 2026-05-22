"""Tests for handlers helper functions."""

from datetime import datetime
from unittest.mock import patch

import pytest

from pyball.settings import PyballConfig


class TestGetNextWeekday:
    """Tests for _get_next_weekday function."""

    def test_get_next_weekday_not_same_day(self):
        """When today is not wednesday, returns next wednesday."""
        from pyball.infrastructure.telegram.bot.handlers.meetup import _get_next_weekday

        settings = PyballConfig(default_week_day="wednesday", default_hour="20:00")

        with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 10, 10, 0)  # Wednesday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = _get_next_weekday(settings)

            # Since today IS wednesday, should be next week
            assert result.weekday() == 2  # wednesday
            assert result.hour == 20
            assert result.minute == 0

    def test_get_next_weekday_same_day_goes_to_next_week(self):
        """When today IS wednesday, returns next wednesday (7 days)."""
        from pyball.infrastructure.telegram.bot.handlers.meetup import _get_next_weekday

        settings = PyballConfig(default_week_day="wednesday", default_hour="20:00")

        with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 10, 10, 0)  # Wednesday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = _get_next_weekday(settings)

            # Should be next wednesday
            assert result > datetime(2024, 1, 10, 20, 0)

    def test_get_next_weekday_monday_from_friday(self):
        """Friday -> Monday (3 days)."""
        from pyball.infrastructure.telegram.bot.handlers.meetup import _get_next_weekday

        settings = PyballConfig(default_week_day="monday", default_hour="19:00")

        with patch("pyball.infrastructure.telegram.bot.handlers.meetup.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 5, 10, 0)  # Friday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = _get_next_weekday(settings)

            assert result.weekday() == 0  # monday
            assert result.hour == 19
            assert result.minute == 0
