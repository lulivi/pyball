"""Integration tests for JsonMeetupRepository (persistence)."""

import shutil
import tempfile
from pathlib import Path
from datetime import datetime

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository


class TestJsonMeetupRepository:
    """Integration tests for JsonMeetupRepository."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)

        assert found is not None
        assert found.date == meetup.date
        assert found.location == "Test Field"

    def test_find_by_date(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_date(datetime(2024, 1, 15).date())

        assert found is not None
        assert found.id == meetup.id

    def test_find_all(self):
        m1 = Meetup.create(datetime(2024, 1, 10), "Test Field")
        m2 = Meetup.create(datetime(2024, 1, 15), "Test Field")
        self.repo.save(m1)
        self.repo.save(m2)

        all_meetups = self.repo.find_all()

        assert len(all_meetups) == 2
        assert all_meetups[0].date < all_meetups[1].date

    def test_save_with_teams(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        meetup.create_balanced_teams(__import__("random"))

        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)
        assert found.teams is not None
        assert len(found.teams) == 2

    def test_delete(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        self.repo.delete(meetup.id)

        found = self.repo.find_by_id(meetup.id)
        assert found is None
