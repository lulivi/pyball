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
"""Parse callup use case: fuzzy-match players and extract the meetup date."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from pyball.application.meetup.parse_callup_text import MatchedPlayer, ParseCallupText
from pyball.domain.player.repository import PlayerRepository


@dataclass
class CallupParseOutcome:
    """Result of parsing a callup: matched players plus the extracted date."""

    titulars: list[MatchedPlayer]
    reserves: list[MatchedPlayer]
    date: datetime


class ParseCallup:
    """Use case orchestrating callup text parsing and date extraction."""

    def __init__(self, player_repository: PlayerRepository, default_hour: str):
        """Initialize with the player repository and the default meetup hour."""
        self.player_repository = player_repository
        self.default_hour = default_hour

    def execute(self, text: str) -> CallupParseOutcome:
        """Parse a callup text into matched players and a meetup datetime."""
        players = self.player_repository.find_all()
        result = ParseCallupText().execute(text, players)
        return CallupParseOutcome(
            titulars=result.titulars,
            reserves=result.reserves,
            date=_extract_callup_date(text, self.default_hour),
        )


def _extract_callup_date(text: str, default_hour: str) -> datetime:
    """Extract the meetup date from a callup header line using locale-aware strptime.

    Tries each line as '%A %d %B' (e.g. 'lunes 18 mayo'). Falls back to today
    when no line matches. If the parsed date is more than 7 days in the past,
    bumps to the next year.
    """
    try:
        hour, minute = (int(p) for p in default_hour.split(":", 1))
    except ValueError:
        hour, minute = 20, 0
    today = datetime.now()
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        try:
            parsed = datetime.strptime(" ".join(parts[:3]).lower(), "%A %d %B")
        except ValueError:
            continue
        candidate = datetime(today.year, parsed.month, parsed.day, hour, minute)
        if candidate < today - timedelta(days=7):
            candidate = candidate.replace(year=today.year + 1)
        return candidate
    return datetime(today.year, today.month, today.day, hour, minute)
