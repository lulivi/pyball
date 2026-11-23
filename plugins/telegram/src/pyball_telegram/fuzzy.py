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

"""Finding a player by a partial or misspelt name."""

from __future__ import annotations

import difflib

from pyball_telegram.api import Player


def match_player(query: str, players: list[Player]) -> Player:
    """Return the one player whose name is ``query``, or the one closest to it.

    Raises ValueError when no player or more than one matches.
    """
    query = query.strip().lower()
    if not query:
        raise ValueError("Query cannot be empty")
    matches = [p for p in players if p.name.lower() == query]
    if not matches:
        close = difflib.get_close_matches(query, [p.name.lower() for p in players], n=3)
        matches = [p for p in players if p.name.lower() in close]
    if not matches:
        raise ValueError(f"Player not found: {query}")
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        raise ValueError(f"Multiple players match '{query}': {names}")
    return matches[0]
