import difflib
from dataclasses import dataclass


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy name matching."""
    player_id: str
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