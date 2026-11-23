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

"""Integration tests for JsonPlayerRepository (persistence)."""

import json
import shutil
import tempfile
from pathlib import Path

from pyball.domain.player.models import Player
from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository


class TestJsonPlayerRepository:
    """Integration tests for JsonPlayerRepository."""

    def setup_method(self):
        """Create a temporary file and repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = Path(self.temp_dir) / "players.json"
        self.repo = JsonPlayerRepository(self.file_path)

    def teardown_method(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        """Saving a player allows it to be retrieved by ID."""
        player = Player.create("Luis", "regular")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)

        assert found is not None
        assert found.name == "Luis"
        assert found.group == "regular"
        assert found.id == player.id

    def test_find_by_name(self):
        """A saved player can be found by exact name."""
        player = Player.create("Carlos", "regular")
        self.repo.save(player)

        found = self.repo.find_by_name("Carlos")

        assert found is not None
        assert found.id == player.id

    def test_find_by_name_case_insensitive(self):
        """Name lookup is case-insensitive."""
        player = Player.create("Ana", "regular")
        self.repo.save(player)

        found = self.repo.find_by_name("ana")

        assert found is not None
        assert found.id == player.id

    def test_find_all(self):
        """find_all returns every saved player."""
        p1 = Player.create("One", "regular")
        p2 = Player.create("Two", "substitute")
        self.repo.save(p1)
        self.repo.save(p2)

        all_players = self.repo.find_all()

        assert len(all_players) == 2

    def test_delete(self):
        """Deleting a player makes them unfindable by ID."""
        player = Player.create("ToDelete", "regular")
        self.repo.save(player)

        self.repo.delete(player.id)

        found = self.repo.find_by_id(player.id)
        assert found is None

    def test_update_player(self):
        """Re-saving a modified player persists the updated fields."""
        player = Player.create("Original", "regular")
        self.repo.save(player)

        player.group = "substitute"
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)
        assert found.group == "substitute"

    def test_save_and_find_by_id_with_position(self):
        """Saving a player with a position persists and reloads it."""
        player = Player.create("Iker", "regular", position="portero")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)

        assert found is not None
        assert found.position == "portero"

    def test_find_all_defaults_position_to_none_for_legacy_file(self):
        """Players saved before this field existed load with position=None."""
        player = Player.create("Legacy", "regular")
        self.repo.save(player)
        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        del data["players"][0]["position"]
        self.file_path.write_text(json.dumps(data), encoding="utf-8")

        found = self.repo.find_by_id(player.id)

        assert found.position is None

    def test_update_player_position(self):
        """Re-saving a player after set_position persists the new position."""
        player = Player.create("Original", "regular")
        self.repo.save(player)

        player.set_position("delantero")
        self.repo.save(player)

        found = self.repo.find_by_id(player.id)
        assert found.position == "delantero"
