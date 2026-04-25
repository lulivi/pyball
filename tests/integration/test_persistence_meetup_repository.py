"""Integration tests for JsonMeetupRepository (persistence)."""

import shutil
import tempfile
from datetime import datetime, time
from pathlib import Path

from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository


class TestJsonMeetupRepository:
    """Integration tests for JsonMeetupRepository."""

    def setup_method(self):
        """Create a temporary directory and repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        """Saving a meetup allows it to be retrieved by ID."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)

        assert found is not None
        assert found.date == meetup.date
        assert found.location == "Test Field"

    def test_find_by_date(self):
        """A saved meetup can be found by its calendar date."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_date(datetime(2024, 1, 15).date())

        assert found is not None
        assert found.id == meetup.id

    def test_find_all(self):
        """find_all returns all saved meetups ordered by date."""
        m1 = Meetup.create(datetime(2024, 1, 10), "Test Field")
        m2 = Meetup.create(datetime(2024, 1, 15), "Test Field")
        self.repo.save(m1)
        self.repo.save(m2)

        all_meetups = self.repo.find_all()

        assert len(all_meetups) == 2
        assert all_meetups[0].date < all_meetups[1].date

    def test_save_with_teams(self):
        """Saving a meetup with teams persists the team data."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)
        assert found.teams is not None
        assert len(found.teams) == 2

    def test_delete(self):
        """Deleting a meetup makes it unfindable by ID."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        self.repo.delete(meetup.id)

        found = self.repo.find_by_id(meetup.id)
        assert found is None


class TestJsonMeetupRepositoryResult:
    """Integration tests for MatchResult persistence."""

    def setup_method(self):
        """Create a temporary directory and repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_meetup_with_result(self):
        """A meetup with a MatchResult round-trips through JSON correctly."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        scorer = PlayerId.generate()
        assistant = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer,
            assistant_id=assistant,
            team="A",
            timestamp=time(20, 15),
        )
        result = MatchResult(score_a=2, score_b=1, events=(event,))
        meetup.set_result(result)

        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)

        assert loaded is not None
        assert loaded.result is not None
        assert loaded.result.score_a == 2
        assert loaded.result.score_b == 1
        assert len(loaded.result.events) == 1
        assert loaded.result.events[0].scorer_id == scorer
        assert loaded.result.events[0].assistant_id == assistant
        assert loaded.result.events[0].team == "A"
        assert loaded.result.events[0].timestamp == time(20, 15)

    def test_save_and_load_meetup_without_result(self):
        """A meetup with no result loads with result=None."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)
        assert loaded is not None
        assert loaded.result is None
