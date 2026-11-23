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
