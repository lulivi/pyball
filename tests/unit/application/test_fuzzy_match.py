"""Tests for fuzzy_match_player function."""

import pytest

from pyball.application.fuzzy_match import fuzzy_match_player


class MockPlayer:
    """Minimal player stub for fuzzy match tests."""

    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name


def test_fuzzy_match_exact():
    """Exact name match returns the correct player."""
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mario", players)
    assert result.name == "Mario"


def test_fuzzy_match_partial():
    """Partial prefix match returns the unique matching player."""
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mar", players)
    assert result.name == "Mario"


def test_fuzzy_match_no_match():
    """No match raises ValueError."""
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    with pytest.raises(ValueError, match="Player not found"):
        fuzzy_match_player("Pippo", players)


def test_fuzzy_match_ambiguous():
    """Multiple partial matches raise ValueError."""
    players = [MockPlayer("1", "Marco"), MockPlayer("2", "Marcos")]
    with pytest.raises(ValueError, match="Multiple players match"):
        fuzzy_match_player("Mar", players)
