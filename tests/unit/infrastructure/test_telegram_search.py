"""Tests for the substitute search target helpers."""

import pytest

from pyball.infrastructure.telegram.search import next_search_target, update_search_target


@pytest.mark.parametrize(
    "count, expected",
    [(0, 10), (9, 10), (10, 12), (11, 12), (12, 15), (14, 15), (15, None), (20, None)],
)
def test_next_search_target(count, expected):
    """Opening targets the first threshold strictly above the roster size."""
    assert next_search_target(count) == expected


@pytest.mark.parametrize(
    "target, count, expected",
    [
        (None, 5, None),  # closed stays closed
        (10, 9, 10),  # still missing one
        (10, 10, None),  # reached
        (12, 10, None),  # 11 -> 10 after a leave: target drops to 10, complete
        (10, 8, 10),  # 9 -> 8: target stays 10
        (15, 12, None),  # 13 -> 12: complete at 12
        (15, 13, 15),  # still searching
        (12, 16, None),  # overshoot closes
    ],
)
def test_update_search_target(target, count, expected):
    """The target only moves down, and the search closes once reached."""
    assert update_search_target(target, count) == expected
