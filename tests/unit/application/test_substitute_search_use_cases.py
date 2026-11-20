"""Tests for the capacity and substitute search use cases."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import (
    CloseSubstituteSearch,
    OpenSubstituteSearch,
    SetMeetupCapacity,
)
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup

DATE = datetime(2026, 7, 15, 20, 0)


def _repo(meetup: Meetup | None) -> MagicMock:
    repo = MagicMock()
    repo.find_by_datetime.return_value = meetup
    return repo


def test_set_capacity_saves():
    """SetMeetupCapacity changes and persists the capacity."""
    meetup = Meetup.create(DATE, "Campo")
    repo = _repo(meetup)
    assert SetMeetupCapacity(repo).execute(DATE, 14).capacity == 14
    repo.save.assert_called_once_with(meetup)


def test_open_and_close_search_save():
    """Opening then closing a search persists each change."""
    meetup = Meetup.create(DATE, "Campo")
    repo = _repo(meetup)
    assert OpenSubstituteSearch(repo).execute(DATE).substitute_search
    assert not CloseSubstituteSearch(repo).execute(DATE).substitute_search
    assert repo.save.call_count == 2


@pytest.mark.parametrize(
    "run",
    [
        lambda repo: SetMeetupCapacity(repo).execute(DATE, 12),
        lambda repo: OpenSubstituteSearch(repo).execute(DATE),
        lambda repo: CloseSubstituteSearch(repo).execute(DATE),
    ],
)
def test_missing_meetup_raises(run):
    """Every use case reports a missing meetup."""
    with pytest.raises(MeetupNotFoundError):
        run(_repo(None))
