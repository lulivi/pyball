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
"""Tests for ParseCallupText use case."""

from pyball.application.meetup.parse_callup_text import (
    ParseCallupText,
    _clean_name,
    _split_sections,
)
from pyball.domain.player.models import Player, PlayerId


def _make_player(name: str) -> Player:
    return Player(id=PlayerId.generate(), name=name, group="regular")


CALLUP_TEXT = """\
Lunes 18 Mayo
1. Juande
2. David Quesada
3. Luvo
4. Luis Sobrino
5. Paco G.
6. Valen
7. José Gualda
8. ⁠Simón
9. Sergio A
10. Zambrano
11. Nacho
12. ⁠Jesús (Luvo)
13. Iván 🧤
14. Sergio Peche

Reservas
- Manu
- Christian
"""


class TestSplitSections:
    """Tests for the _split_sections helper function."""

    def test_extracts_titular_names(self):
        """Numbered lines before Reservas are returned as titulars."""
        titulars, _ = _split_sections(CALLUP_TEXT)
        assert "Juande" in titulars
        assert "David Quesada" in titulars
        assert len(titulars) == 14

    def test_extracts_reserve_names(self):
        """Bulleted lines after Reservas are returned as reserves."""
        _, reserves = _split_sections(CALLUP_TEXT)
        assert "Manu" in reserves
        assert "Christian" in reserves
        assert len(reserves) == 2

    def test_header_line_not_included(self):
        """The date header line is not included in titulars."""
        titulars, _ = _split_sections(CALLUP_TEXT)
        assert "Lunes 18 Mayo" not in titulars

    def test_empty_text_returns_empty_lists(self):
        """Empty input returns two empty lists."""
        titulars, reserves = _split_sections("")
        assert not titulars
        assert not reserves

    def test_ignores_convocatoria_copy_panel_header_lines(self):
        """The /manage roster copy panel's emoji header lines are ignored, not misparsed.

        Verifies only the player-list half of the round trip: that
        _split_sections() correctly extracts the numbered player list and
        doesn't mistake the emoji/markdown header lines for player names. The
        date half is covered separately by
        test_parse_callup.test_roster_panel_header_line_is_parsed, which
        exercises the full ParseCallup.execute() including date extraction.
        """
        text = "📅 *Convocatoria: Lunes 18 Mayo*\n📍 *Parque*\n\n1. Juande\n2. Luvo\n"
        titulars, reserves = _split_sections(text)
        assert titulars == ["Juande", "Luvo"]
        assert not reserves


class TestCleanName:
    """Tests for the _clean_name helper function."""

    def test_strips_emoji(self):
        """Emoji characters are removed from the name."""
        assert _clean_name("Iván 🧤") == "Iván"

    def test_strips_parenthetical_note(self):
        """Parenthetical suffixes (e.g. team labels) are removed."""
        assert _clean_name("Jesús (Luvo)") == "Jesús"

    def test_strips_zero_width_chars(self):
        """Zero-width characters (e.g. U+2060 WORD JOINER) are removed."""
        assert _clean_name("⁠Simón") == "Simón"

    def test_preserves_accented_chars(self):
        """Accented Spanish characters are preserved."""
        assert _clean_name("José Gualda") == "José Gualda"


class TestParseCallupText:
    """Tests for the ParseCallupText use case."""

    players: list[Player]
    use_case: ParseCallupText

    def setup_method(self):
        """Reset players and use case before each test."""
        self.players = [
            _make_player("Juande"),
            _make_player("David Quesada"),
            _make_player("Luvo"),
            _make_player("Luis Sobrino"),
            _make_player("Paco García"),
            _make_player("Valentín"),
            _make_player("José Gualda"),
            _make_player("Simón"),
            _make_player("Sergio Arancibia"),
            _make_player("Zambrano"),
            _make_player("Nacho"),
            _make_player("Jesús Romero"),
            _make_player("Iván"),
            _make_player("Sergio Peche"),
            _make_player("Manu"),
            _make_player("Christian"),
        ]
        self.use_case = ParseCallupText()

    def test_high_confidence_match_has_player_id(self):
        """An exact name match yields a resolved player_id and confidence >= 0.9."""
        result = self.use_case.execute("1. Juande\n", self.players)
        assert len(result.titulars) == 1
        assert result.titulars[0].player_id is not None
        assert result.titulars[0].name == "Juande"
        assert result.titulars[0].confidence >= 0.9

    def test_low_confidence_returns_candidates(self):
        """An ambiguous partial name yields no player_id but a non-empty candidates list."""
        result = self.use_case.execute("1. Sergi\n", self.players)
        match = result.titulars[0]
        assert match.player_id is None
        assert len(match.candidates) >= 1

    def test_no_match_returns_empty_candidates(self):
        """A name with no similarity to any player yields empty candidates and zero confidence."""
        result = self.use_case.execute("1. Zzzzunknown\n", self.players)
        match = result.titulars[0]
        assert match.player_id is None
        assert not match.candidates
        assert match.confidence == 0.0

    def test_reserves_are_separated(self):
        """Reserves section is parsed into the reserves list, titulars into titulars."""
        result = self.use_case.execute(CALLUP_TEXT, self.players)
        assert len(result.titulars) == 14
        assert len(result.reserves) == 2

    def test_emoji_stripped_before_matching(self):
        """Emoji in a raw name is stripped before fuzzy-matching."""
        result = self.use_case.execute("1. Iván 🧤\n", self.players)
        assert result.titulars[0].name == "Iván"

    def test_parenthetical_stripped_before_matching(self):
        """Parenthetical note is stripped before fuzzy-matching."""
        result = self.use_case.execute("1. Jesús (Luvo)\n", self.players)
        assert result.titulars[0].name == "Jesús Romero"

    def test_exact_name_wins_when_tokens_overlap(self):
        """Exact full-name match resolves confidently even when other players share the token."""
        players_with_luvo = self.players + [
            _make_player("Alberto Luvo"),
            _make_player("Alvaro Luvo"),
            _make_player("Diego Luvo"),
        ]
        result = self.use_case.execute("1. Luvo\n", players_with_luvo)
        match = result.titulars[0]
        assert match.player_id is not None
        assert match.name == "Luvo"
        assert match.confidence == 1.0
