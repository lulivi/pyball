"""Integration tests for JsonPlayerRepository (persistence)."""

import json
import shutil
import tempfile

from datetime import datetime
from pathlib import Path

from pyball.domain.player.models import Player, PlayerId
from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository


class TestJsonPlayerRepository:
    """Integration tests for JsonPlayerRepository."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = Path(self.temp_dir) / "players.json"
        self.repo = JsonPlayerRepository(self.file_path)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        player = Player.create("Luis", "regular")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)

        assert found is not None
        assert found.name == "Luis"
        assert found.group == "regular"
        assert found.id == player.id

    def test_find_by_name(self):
        player = Player.create("Carlos", "regular")
        self.repo.save(player)

        found = self.repo.find_by_name("Carlos")

        assert found is not None
        assert found.id == player.id

    def test_find_by_name_case_insensitive(self):
        player = Player.create("Ana", "regular")
        self.repo.save(player)

        found = self.repo.find_by_name("ana")

        assert found is not None
        assert found.id == player.id

    def test_find_all(self):
        p1 = Player.create("One", "regular")
        p2 = Player.create("Two", "substitute")
        self.repo.save(p1)
        self.repo.save(p2)

        all_players = self.repo.find_all()

        assert len(all_players) == 2

    def test_delete(self):
        player = Player.create("ToDelete", "regular")
        self.repo.save(player)

        self.repo.delete(player.id)

        found = self.repo.find_by_id(player.id)
        assert found is None

    def test_update_player(self):
        player = Player.create("Original", "regular")
        self.repo.save(player)

        player.group = "substitute"
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)
        assert found.group == "substitute"
