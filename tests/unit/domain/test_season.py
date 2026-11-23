# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
