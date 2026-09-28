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
"""Substitute search target rules — how many players a Telegram search is looking for."""

SEARCH_THRESHOLDS: tuple[int, ...] = (10, 12, 15)


def next_search_target(player_count: int) -> int | None:
    """Return the target for a new search, or None if the roster is already at the top."""
    return next((t for t in SEARCH_THRESHOLDS if t > player_count), None)


def update_search_target(target: int | None, player_count: int) -> int | None:
    """Return the search target after a roster change; None means the search is closed.

    The target only moves down: a leave that lands the roster on a lower threshold
    (e.g. 11 -> 10 while searching for 12) completes the search at that threshold.
    """
    if target is None:
        return None
    floor = next((t for t in SEARCH_THRESHOLDS if t >= player_count), target)
    target = min(target, floor)
    return None if player_count >= target else target
