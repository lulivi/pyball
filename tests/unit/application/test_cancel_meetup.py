"""Tests for CancelMeetup use case."""

import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import CancelMeetup
from pyball.domain.meetup.errors import MeetupHasRecordedResultsError, MeetupNotFoundError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team


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

    def test_raises_when_active_meetup_has_recorded_results(self):
        """MeetupHasRecordedResultsError is raised and nothing is deleted once a result exists."""
        meetup = _active_meetup(datetime(2026, 6, 8, 20, 0))
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        meetup.add_match(
            Match(
                teams_playing=(meetup.teams[0], meetup.teams[1]),
                result=MatchResult(score_a=1, score_b=0, events=()),
            )
        )
        repo = MagicMock()
        repo.find_all.return_value = [meetup]

        with pytest.raises(MeetupHasRecordedResultsError):
            CancelMeetup(repo).execute()

        repo.delete.assert_not_called()

    def test_execute_logs_cancellation_at_info(self, caplog):
        """Cancelling a meetup emits one INFO record on its logger."""
        meetup = _active_meetup(datetime(2026, 6, 8, 20, 0))
        repo = MagicMock()
        repo.find_all.return_value = [meetup]

        with caplog.at_level(logging.INFO, logger="pyball.application.meetup.cancel_meetup"):
            CancelMeetup(repo).execute()

        recs = [r for r in caplog.records if r.name == "pyball.application.meetup.cancel_meetup"]
        assert len(recs) == 1
        assert recs[0].levelno == logging.INFO
        assert "cancelled" in recs[0].getMessage().lower()
