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
