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
"""Tests for UpdateMeetupDate use case."""

from datetime import datetime

import pytest

from pyball.application.meetup.update_meetup_date import UpdateMeetupDate
from pyball.domain.meetup.errors import DuplicateMeetupError, MeetupNotFoundError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team


class FakeMeetupRepository:
    """In-memory meetup repository for testing."""

    def __init__(self):
        """Initialize with empty meetups list."""
        self.meetups = []

    def save(self, meetup):
        """Save or update a meetup."""
        self.meetups = [m if m.id != meetup.id else meetup for m in self.meetups]
        if meetup not in self.meetups:
            self.meetups.append(meetup)

    def find_by_datetime(self, date):
        """Find meetup by datetime."""
        return next((m for m in self.meetups if m.date == date), None)

    def find_by_id(self, meetup_id):
        """Find meetup by id."""
        return next((m for m in self.meetups if m.id == meetup_id), None)

    def find_all(self):
        """Return all meetups."""
        return list(self.meetups)

    def delete(self, meetup_id):
        """Delete a meetup by id."""
        self.meetups = [m for m in self.meetups if m.id != meetup_id]

    def delete_by_datetime(self, date: datetime) -> None:
        """Remove the meetup at the given datetime."""
        self.meetups = [m for m in self.meetups if m.date != date]


class TestUpdateMeetupDate:
    """Tests for UpdateMeetupDate use case."""

    def test_changes_date_and_persists(self):
        """execute moves the meetup to a new date and persists it."""
        repo = FakeMeetupRepository()
        old_date = datetime(2026, 6, 8, 20, 0)
        new_date = datetime(2026, 6, 15, 20, 0)
        meetup = Meetup.create(date=old_date, location="Parque Central")
        repo.meetups.append(meetup)

        use_case = UpdateMeetupDate(repo)
        result = use_case.execute(old_date, new_date)

        assert result.date == new_date
        assert repo.find_by_datetime(new_date) is not None
        assert repo.find_by_datetime(old_date) is None

    def test_raises_when_meetup_not_found(self):
        """execute raises MeetupNotFoundError when no meetup at old_date."""
        repo = FakeMeetupRepository()
        use_case = UpdateMeetupDate(repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2026, 6, 8, 20, 0), datetime(2026, 6, 15, 20, 0))

    def test_raises_when_meetup_is_closed(self):
        """execute raises ValueError when the meetup already has a result."""
        repo = FakeMeetupRepository()
        old_date = datetime(2026, 6, 8, 20, 0)
        meetup = Meetup.create(date=old_date, location="Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        meetup.set_teams([team_a, team_b])
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 1, ())))
        meetup.close()
        repo.meetups.append(meetup)

        use_case = UpdateMeetupDate(repo)
        with pytest.raises(ValueError, match="finished"):
            use_case.execute(old_date, datetime(2026, 6, 15, 20, 0))

    def test_raises_when_new_date_already_taken(self):
        """execute raises DuplicateMeetupError when another meetup exists at new_date."""
        repo = FakeMeetupRepository()
        old_date = datetime(2026, 6, 8, 20, 0)
        new_date = datetime(2026, 6, 15, 20, 0)
        meetup = Meetup.create(date=old_date, location="Parque Central")
        conflict = Meetup.create(date=new_date, location="Parque Central")
        repo.meetups.extend([meetup, conflict])

        use_case = UpdateMeetupDate(repo)
        with pytest.raises(DuplicateMeetupError):
            use_case.execute(old_date, new_date)
