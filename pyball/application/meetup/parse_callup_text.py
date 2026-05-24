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
"""Parse callup text use case."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from pyball.domain.player.models import Player

_CONFIDENT_THRESHOLD = 0.9
_CANDIDATE_THRESHOLD = 0.5
_TOP_CANDIDATES = 3


@dataclass
class PlayerCandidate:
    """A candidate player with a similarity score."""

    player_id: str
    name: str
    confidence: float


@dataclass
class MatchedPlayer:
    """Result of matching a raw callup name against the player database."""

    raw: str
    player_id: str | None
    name: str | None
    confidence: float
    candidates: list[PlayerCandidate] = field(default_factory=list)


@dataclass
class ParseResult:
    """Parsed callup split into titular and reserve matches."""

    titulars: list[MatchedPlayer]
    reserves: list[MatchedPlayer]


class ParseCallupText:
    """Use case: parse a WhatsApp callup message and match names to DB players."""

    def execute(self, text: str, players: list[Player]) -> ParseResult:
        """Parse callup text and fuzzy-match each name.

        Args:
            text: Raw WhatsApp callup message.
            players: All players from the DB.

        Returns:
            ParseResult with titulars and reserves lists.
        """
        titulars_raw, reserves_raw = _split_sections(text)
        return ParseResult(
            titulars=[_match_name(raw, players) for raw in titulars_raw],
            reserves=[_match_name(raw, players) for raw in reserves_raw],
        )


def _split_sections(text: str) -> tuple[list[str], list[str]]:
    """Split callup text into titular names and reserve names."""
    lines = text.splitlines()
    titulars: list[str] = []
    reserves: list[str] = []
    in_reserves = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"reservas?", stripped, re.IGNORECASE):
            in_reserves = True
            continue
        numbered = re.match(r"^\d+\.\s*(.+)", stripped)
        bulleted = re.match(r"^[-•]\s*(.+)", stripped)
        if numbered and not in_reserves:
            titulars.append(numbered.group(1).strip())
        elif numbered:
            reserves.append(numbered.group(1).strip())
        elif bulleted and in_reserves:
            reserves.append(bulleted.group(1).strip())
    return titulars, reserves


def _clean_name(raw: str) -> str:
    """Strip emojis, zero-width chars, and parenthetical notes from a raw name."""
    raw = re.sub(r"\s*\([^)]*\)", "", raw)
    raw = re.sub(r"[\u2060\u200b\u200c\u200d\ufeff]", "", raw)
    raw = re.sub(r"[^\w\s\-]", "", raw)
    return raw.strip()


def _match_name(raw: str, players: list[Player]) -> MatchedPlayer:
    """Fuzzy-match a raw name string against all players."""
    cleaned = _clean_name(raw)
    candidates = _score_candidates(cleaned, players)
    if not candidates:
        return MatchedPlayer(raw=raw, player_id=None, name=None, confidence=0.0)
    top = candidates[0]
    confident = [c for c in candidates if c.confidence >= _CONFIDENT_THRESHOLD]
    if len(confident) == 1:
        return MatchedPlayer(
            raw=raw, player_id=top.player_id, name=top.name, confidence=top.confidence
        )
    return MatchedPlayer(
        raw=raw,
        player_id=None,
        name=None,
        confidence=top.confidence,
        candidates=candidates[:_TOP_CANDIDATES],
    )


def _score_candidates(query: str, players: list[Player]) -> list[PlayerCandidate]:
    """Return players scored by similarity to query, filtered by threshold."""
    query_lower = query.lower()
    scored = [
        PlayerCandidate(
            player_id=str(p.id.value),
            name=p.name,
            confidence=_combined_ratio(query_lower, p.name.lower()),
        )
        for p in players
    ]
    return sorted(
        (c for c in scored if c.confidence >= _CANDIDATE_THRESHOLD),
        key=lambda c: -c.confidence,
    )


def _combined_ratio(query: str, name: str) -> float:
    """Return the best similarity ratio between query and name or its tokens."""
    seq_ratio = difflib.SequenceMatcher(None, query, name).ratio()
    token_ratio = max(
        difflib.SequenceMatcher(None, query, token).ratio() for token in name.split()
    )
    return max(seq_ratio, token_ratio)
