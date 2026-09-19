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
"""Match-outcome and winning-pair-count pure domain helpers."""

from __future__ import annotations

import itertools
from functools import lru_cache

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import PlayerId


def winning_pair_counts(meetups: list[Meetup]) -> dict[tuple[str, str], int]:
    """Return sorted (pid_a, pid_b) -> shared-win count across all given meetups."""
    counts: dict[tuple[str, str], int] = {}
    for meetup in meetups:
        for match in meetup.matches:
            if match.result is None:
                continue
            winner_index = match.result.winner_index()
            if winner_index is None:
                continue
            team = match.teams_playing[winner_index]
            for pid_a, pid_b in itertools.combinations(team.players, 2):
                key = pair_key(pid_a, pid_b)
                counts[key] = counts.get(key, 0) + 1
    return counts


@lru_cache(maxsize=65536)
def pair_key(pid_a: PlayerId, pid_b: PlayerId) -> tuple[str, str]:
    """Return the canonical (smaller, larger) string-id key for a player pair.

    Cached: exhaustive partition scoring recomputes the same few hundred pairs
    millions of times, and the UUID-to-string conversion dominates its runtime.
    """
    key_a, key_b = str(pid_a.value), str(pid_b.value)
    return (key_a, key_b) if key_a <= key_b else (key_b, key_a)
