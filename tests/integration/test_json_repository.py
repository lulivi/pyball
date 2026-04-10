"""Integration tests for JSON repositories."""

import json
import tempfile

from datetime import datetime
from pathlib import Path

import pytest

from pyball.domain.meetup.models import Meetup, MeetupId, Team
from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure import JsonMeetupRepository, JsonPlayerRepository


class TestJsonPlayerRepository:
    """Integration tests for JsonPlayerRepository."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = Path(self.temp_dir) / "players.json"
        self.repo = JsonPlayerRepository(self.file_path)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        player = Player.create("Luis")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)

        assert found is not None
        assert found.name == "Luis"
        assert found.id == player.id

    def test_find_by_name(self):
        player = Player.create("Carlos")
        self.repo.save(player)

        found = self.repo.find_by_name("Carlos")

        assert found is not None
        assert found.id == player.id

    def test_find_by_name_case_insensitive(self):
        player = Player.create("Ana")
        self.repo.save(player)

        found = self.repo.find_by_name("ana")

        assert found is not None
        assert found.id == player.id

    def test_find_all(self):
        p1 = Player.create("One")
        p2 = Player.create("Two")
        self.repo.save(p1)
        self.repo.save(p2)

        all_players = self.repo.find_all()

        assert len(all_players) == 2

    def test_delete(self):
        player = Player.create("ToDelete")
        self.repo.save(player)

        self.repo.delete(player.id)

        found = self.repo.find_by_id(player.id)
        assert found is None

    def test_update_player(self):
        player = Player.create("Original")
        self.repo.save(player)

        player.rename("Updated")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)
        assert found.name == "Updated"


class TestJsonMeetupRepository:
    """Integration tests for JsonMeetupRepository."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)

        assert found is not None
        assert found.date == meetup.date

    def test_find_by_date(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
        self.repo.save(meetup)

        found = self.repo.find_by_date(datetime(2024, 1, 15).date())

        assert found is not None
        assert found.id == meetup.id

    def test_find_all(self):
        m1 = Meetup.create(datetime(2024, 1, 10))
        m2 = Meetup.create(datetime(2024, 1, 15))
        self.repo.save(m1)
        self.repo.save(m2)

        all_meetups = self.repo.find_all()

        assert len(all_meetups) == 2
        assert all_meetups[0].date < all_meetups[1].date

    def test_save_with_teams(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_regular(p1)
        meetup.add_regular(p2)
        meetup.create_balanced_teams(__import__("random"))

        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)
        assert found.teams is not None
        assert len(found.teams) == 2

    def test_delete(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        self.repo.save(meetup)

        self.repo.delete(meetup.id)

        found = self.repo.find_by_id(meetup.id)
        assert found is None
