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
"""Tests for the ParseCallup use case."""

from datetime import datetime, timedelta

from pyball.application.meetup.parse_callup import ParseCallup


class FakePlayerRepository:
    """In-memory player repository returning a fixed list."""

    def __init__(self, players=None):
        self.players = players or []

    def find_all(self):
        """Return the fixed player list."""
        return self.players


def _use_case(default_hour="20:00"):
    """Build a ParseCallup with a fake empty player repository."""
    return ParseCallup(FakePlayerRepository(), default_hour=default_hour)


def test_empty_text_falls_back_to_today_at_default_hour():
    """Empty text yields no players and today's date at the default hour."""
    outcome = _use_case().execute("")
    today = datetime.now()
    assert not outcome.titulars
    assert not outcome.reserves
    assert outcome.date.date() == today.date()
    assert (outcome.date.hour, outcome.date.minute) == (20, 0)


def test_invalid_default_hour_falls_back_to_2000():
    """A bogus default_hour string falls back to 20:00."""
    outcome = _use_case(default_hour="bogus").execute("")
    assert (outcome.date.hour, outcome.date.minute) == (20, 0)


def test_header_line_is_parsed_with_current_locale():
    """A header line matching '%A %d %B' is parsed into the correct date."""
    # Locale-dependent day/month names: build the line from strftime so the
    # test passes under any locale (C in CI, es_ES locally).
    target = datetime.now() + timedelta(days=3)
    line = target.strftime("%A %d %B").lower()

    outcome = _use_case().execute(f"{line}\n")

    assert (outcome.date.month, outcome.date.day) == (target.month, target.day)
    assert (outcome.date.hour, outcome.date.minute) == (20, 0)


def test_date_more_than_a_week_past_bumps_to_next_year():
    """A header date more than 7 days in the past is bumped to the next year."""
    target = datetime.now() - timedelta(days=30)
    line = target.strftime("%A %d %B").lower()

    outcome = _use_case().execute(f"{line}\n")

    assert outcome.date.year == datetime.now().year + 1


def test_roster_panel_header_line_is_parsed():
    """A callup pasted straight from /manage's copy panels still yields the date.

    The roster/teams-box header wraps the date in emoji and markdown
    ("📅 *Convocatoria: <fecha>*"), unlike a plain typed header line — this
    locks in that pasting one of those panels' own generated text back into
    "Pegar convocatoria" recovers the original date instead of silently
    falling back to today.
    """
    target = datetime.now() + timedelta(days=3)
    line = target.strftime("%A %d %B").lower()

    outcome = _use_case().execute(f"📅 *Convocatoria: {line}*\n📍 *Parque*\n\n1. Juande\n")

    assert (outcome.date.month, outcome.date.day) == (target.month, target.day)
    assert (outcome.date.hour, outcome.date.minute) == (20, 0)
