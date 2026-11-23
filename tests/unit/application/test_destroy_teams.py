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

"""Tests for the DestroyTeams use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.destroy_teams import DestroyTeams
from pyball.domain.meetup.errors import (
    MeetupHasNoTeamsError,
    MeetupHasRecordedResultsError,
    MeetupNotFoundError,
)
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team

DATE = datetime(2026, 7, 15, 20, 0)


def _meetup_with_teams():
    meetup = Meetup.create(DATE, "Campo")
    p1, p2 = PlayerId.generate(), PlayerId.generate()
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
    return meetup


class TestDestroyTeams:
    """Tests for DestroyTeams use case."""

    def test_clears_teams_matches_and_closed(self):
        """execute() resets teams/matches/closed and persists the meetup."""
        meetup = _meetup_with_teams()
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        result = DestroyTeams(repo).execute(DATE)

        assert result.teams is None
        assert result.matches == []
        assert not result.closed
        repo.save.assert_called_once_with(meetup)

    def test_raises_when_meetup_not_found(self):
        """execute() raises MeetupNotFoundError when no meetup exists at the date."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None

        with pytest.raises(MeetupNotFoundError):
            DestroyTeams(repo).execute(DATE)

    def test_raises_when_meetup_has_no_teams(self):
        """execute() raises MeetupHasNoTeamsError when there are no teams to destroy."""
        meetup = Meetup.create(DATE, "Campo")
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(MeetupHasNoTeamsError):
            DestroyTeams(repo).execute(DATE)

        repo.save.assert_not_called()

    def test_raises_when_a_match_already_has_a_result(self):
        """execute() raises MeetupHasRecordedResultsError, leaving the meetup untouched."""
        meetup = _meetup_with_teams()
        meetup.add_match(
            Match(
                teams_playing=(meetup.teams[0], meetup.teams[1]),
                result=MatchResult(score_a=1, score_b=0, events=()),
            )
        )
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(MeetupHasRecordedResultsError):
            DestroyTeams(repo).execute(DATE)

        assert meetup.teams is not None
        repo.save.assert_not_called()
