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
"""Tests for UpdateMeetupLocation use case."""

from datetime import datetime

import pytest

from pyball.application.meetup.update_meetup_location import UpdateMeetupLocation
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup


class FakeMeetupRepository:
    """In-memory meetup repository for testing."""

    def __init__(self):
        """Initialize an empty repository."""
        self.meetups = []

    def save(self, meetup):
        """Save or update a meetup."""
        self.meetups = [m if m.id != meetup.id else meetup for m in self.meetups]
        if meetup not in self.meetups:
            self.meetups.append(meetup)

    def find_by_datetime(self, date):
        """Find a meetup by date."""
        return next((m for m in self.meetups if m.date == date), None)

    def find_by_id(self, meetup_id):
        """Find a meetup by ID."""
        return next((m for m in self.meetups if m.id == meetup_id), None)

    def find_all(self):
        """Return all meetups."""
        return list(self.meetups)

    def delete(self, meetup_id):
        """Delete a meetup by ID."""
        self.meetups = [m for m in self.meetups if m.id != meetup_id]


class TestUpdateMeetupLocation:
    """Tests for UpdateMeetupLocation use case."""

    def test_updates_location_and_persists(self):
        """execute changes the meetup location and saves it."""
        repo = FakeMeetupRepository()
        date = datetime(2026, 6, 8, 20, 0)
        meetup = Meetup.create(date=date, location="Parque Central")
        repo.meetups.append(meetup)

        use_case = UpdateMeetupLocation(repo)
        result = use_case.execute(date, "Parque Sur")

        assert result.location == "Parque Sur"
        assert repo.find_by_datetime(date).location == "Parque Sur"

    def test_raises_when_meetup_not_found(self):
        """execute raises MeetupNotFoundError when no meetup at the given date."""
        repo = FakeMeetupRepository()
        use_case = UpdateMeetupLocation(repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2026, 6, 8, 20, 0), "Parque Sur")

    def test_raises_on_empty_location(self):
        """execute propagates ValueError when the new location is blank."""
        repo = FakeMeetupRepository()
        date = datetime(2026, 6, 8, 20, 0)
        meetup = Meetup.create(date=date, location="Parque Central")
        repo.meetups.append(meetup)

        use_case = UpdateMeetupLocation(repo)
        with pytest.raises(ValueError):
            use_case.execute(date, "")
