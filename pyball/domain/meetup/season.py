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
"""Season-boundary pure domain helper: which meetups count as "this season"."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from pyball.domain.meetup.models import Meetup

_SEASON_START_MONTH = 9


@dataclass
class SeasonScope:
    """Meetups partitioned by the season boundary, plus the boundary itself."""

    finished: list[Meetup]
    season_meetups: list[Meetup]
    season_start: datetime


def season_scope(all_meetups: list[Meetup]) -> SeasonScope:
    """Partition finished meetups into season-scoped and all-time from today's season boundary."""
    start = _season_start(date.today())
    finished = [m for m in all_meetups if m.matches and m.matches[-1].result is not None]
    season_meetups = [m for m in finished if m.date.date() >= start]
    return SeasonScope(
        finished=finished,
        season_meetups=season_meetups,
        season_start=datetime.combine(start, datetime.min.time()),
    )


def _season_start(today: date) -> date:
    """Return Sep 1 of the current season year."""
    if today.month >= _SEASON_START_MONTH:
        return date(today.year, _SEASON_START_MONTH, 1)
    return date(today.year - 1, _SEASON_START_MONTH, 1)
