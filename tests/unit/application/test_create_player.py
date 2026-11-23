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

"""Tests for CreatePlayer use case."""

from unittest.mock import MagicMock

import pytest

from pyball.application.player import CreatePlayer
from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player


class TestCreatePlayer:
    """Tests for CreatePlayer use case."""

    def test_create_player_with_group(self):
        """Creating a player with an explicit group assigns it correctly."""
        repo = MagicMock()
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Mario", group="regular")

        assert player.name == "Mario"
        assert player.group == "regular"
        repo.save.assert_called_once()

    def test_create_player_success(self):
        """Creating a unique player saves it to the repository."""
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Luis", group="regular")

        assert player.name == "Luis"
        assert player.group == "regular"
        repo.save.assert_called_once()

    def test_create_duplicate_player_raises(self):
        """Creating a player with a duplicate name raises PlayerAlreadyExistsError."""
        repo = MagicMock()
        repo.find_all.return_value = [Player.create(name="Luis", group="regular")]
        use_case = CreatePlayer(repo)

        with pytest.raises(PlayerAlreadyExistsError):
            use_case.execute(name="Luis", group="regular")

    def test_create_player_with_whitespace(self):
        """Leading and trailing whitespace is stripped from the player name."""
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="  Luis  ", group="regular")

        assert player.name == "Luis"
        assert player.group == "regular"
        repo.save.assert_called_once()

    def test_create_player_with_position(self):
        """Creating a player with a position assigns it correctly."""
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Iker", group="regular", position="portero")

        assert player.position == "portero"
        repo.save.assert_called_once()

    def test_create_player_without_position_defaults_to_none(self):
        """Creating a player without a position leaves it unset."""
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Iker", group="regular")

        assert player.position is None
