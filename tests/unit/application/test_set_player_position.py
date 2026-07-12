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
"""Tests for SetPlayerPosition use case."""

from unittest.mock import MagicMock

from pyball.application.player.set_position import SetPlayerPosition
from pyball.domain.player.models import Player


def test_set_player_position():
    """Setting a player's position updates and saves it."""
    player = Player.create(name="Mario", group="regular")
    repo = MagicMock()
    repo.find_by_id.return_value = player

    use_case = SetPlayerPosition(repo)
    result = use_case.execute(str(player.id.value), "defensa")

    assert result.position == "defensa"
    repo.save.assert_called_once()


def test_set_player_position_to_none():
    """Setting a player's position to None clears it."""
    player = Player.create(name="Mario", group="regular", position="delantero")
    repo = MagicMock()
    repo.find_by_id.return_value = player

    use_case = SetPlayerPosition(repo)
    result = use_case.execute(str(player.id.value), None)

    assert result.position is None
