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
"""Fuzzy matching for player names."""

import difflib
from dataclasses import dataclass

from pyball.domain.player.models import PlayerId


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy name matching."""

    player_id: PlayerId
    name: str


def fuzzy_match_player(query: str, players: list) -> FuzzyMatchResult:
    """Find player by fuzzy name match.

    Args:
        query: Search query (partial or full name)
        players: List of objects with 'id' and 'name' attributes

    Returns:
        FuzzyMatchResult with matched player

    Raises:
        ValueError: If no match or multiple ambiguous matches
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    query = query.strip().lower()
    names = [(p.id, p.name, p.name.lower()) for p in players]

    matches = [(pid, name) for pid, name, lower_name in names if lower_name == query]

    if not matches:
        close = difflib.get_close_matches(query, [n[2] for n in names], n=3, cutoff=0.6)
        matches = [(pid, name) for pid, name, lower_name in names if lower_name in close]

    if not matches:
        raise ValueError(f"Player not found: {query}")

    if len(matches) > 1:
        names_str = ", ".join(m[1] for m in matches)
        raise ValueError(f"Multiple players match '{query}': {names_str}")

    return FuzzyMatchResult(player_id=matches[0][0], name=matches[0][1])
