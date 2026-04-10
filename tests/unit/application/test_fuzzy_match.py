import pytest

from pyball.application.fuzzy_match import fuzzy_match_player


class MockPlayer:
    def __init__(self, player_id, name):
        self.id = player_id
        self.name = name


def test_fuzzy_match_exact():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mario", players)
    assert result.name == "Mario"


def test_fuzzy_match_partial():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    result = fuzzy_match_player("Mar", players)
    assert result.name == "Mario"


def test_fuzzy_match_no_match():
    players = [MockPlayer("1", "Mario"), MockPlayer("2", "Luigi")]
    with pytest.raises(ValueError, match="Player not found"):
        fuzzy_match_player("Pippo", players)


def test_fuzzy_match_ambiguous():
    players = [MockPlayer("1", "Marco"), MockPlayer("2", "Marcos")]
    with pytest.raises(ValueError, match="Multiple players match"):
        fuzzy_match_player("Mar", players)
