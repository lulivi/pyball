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
