"""Tests for the LockMeetup use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.lock_meetup import LockMeetup
from pyball.domain.meetup.errors import MeetupHasNoTeamsError, MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, PlayerId, Team

DATE = datetime(2026, 7, 15, 20, 0)


class TestLockMeetup:
    """Tests for LockMeetup use case."""

    def test_locks_meetup_with_teams(self):
        """execute() sets locked=True and persists the meetup."""
        meetup = Meetup.create(DATE, "Campo")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        result = LockMeetup(repo).execute(DATE)

        assert result.locked
        repo.save.assert_called_once_with(meetup)

    def test_raises_when_meetup_not_found(self):
        """execute() raises MeetupNotFoundError when no meetup exists at the date."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None

        with pytest.raises(MeetupNotFoundError):
            LockMeetup(repo).execute(DATE)

    def test_raises_when_meetup_has_no_teams(self):
        """execute() raises MeetupHasNoTeamsError when teams haven't been generated yet."""
        meetup = Meetup.create(DATE, "Campo")
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(MeetupHasNoTeamsError):
            LockMeetup(repo).execute(DATE)

        repo.save.assert_not_called()
