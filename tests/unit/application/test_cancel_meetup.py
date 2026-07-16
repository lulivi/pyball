"""Tests for CancelMeetup use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import CancelMeetup
from pyball.domain.meetup.errors import MeetupLockedError, MeetupNotFoundError
from pyball.domain.meetup.models import Meetup


def _active_meetup(date: datetime) -> Meetup:
    return Meetup.create(date, "Campo")


class TestCancelMeetup:
    """Tests for CancelMeetup use case."""

    def test_deletes_most_recent_active_meetup_and_returns_it(self):
        """The most recent active meetup is deleted by ID and returned."""
        older = _active_meetup(datetime(2026, 6, 1, 20, 0))
        newer = _active_meetup(datetime(2026, 6, 8, 20, 0))
        repo = MagicMock()
        repo.find_all.return_value = [older, newer]

        result = CancelMeetup(repo).execute()

        assert result is newer
        repo.delete.assert_called_once_with(newer.id)

    def test_raises_when_no_meetups_exist(self):
        """MeetupNotFoundError raised and nothing deleted when repository is empty."""
        repo = MagicMock()
        repo.find_all.return_value = []

        with pytest.raises(MeetupNotFoundError):
            CancelMeetup(repo).execute()

        repo.delete.assert_not_called()

    def test_raises_when_only_closed_meetups_exist(self):
        """MeetupNotFoundError raised when every meetup is already closed."""
        closed = MagicMock()
        closed.closed = True
        repo = MagicMock()
        repo.find_all.return_value = [closed]

        with pytest.raises(MeetupNotFoundError):
            CancelMeetup(repo).execute()

        repo.delete.assert_not_called()

    def test_raises_when_active_meetup_is_locked(self):
        """MeetupLockedError is raised and nothing is deleted when the meetup is locked."""
        meetup = _active_meetup(datetime(2026, 6, 8, 20, 0))
        meetup.locked = True
        repo = MagicMock()
        repo.find_all.return_value = [meetup]

        with pytest.raises(MeetupLockedError):
            CancelMeetup(repo).execute()

        repo.delete.assert_not_called()
