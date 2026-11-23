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

"""Shared fixtures for integration tests."""

from unittest.mock import MagicMock

import pytest

from pyball.application.container import Container
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository
from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository

# pylint: disable=redefined-outer-name


@pytest.fixture
def tmp_data(tmp_path):
    """Temp directory with meetups/ subdir pre-created."""
    (tmp_path / "meetups").mkdir()
    return tmp_path


@pytest.fixture
def real_container(tmp_data):
    """Real Container with JSON repos backed by tmp_data."""
    settings_mock = MagicMock()
    settings_mock.pyball.location = "Test Field"
    settings_mock.pyball.meetup_capacity = 10
    settings_mock.pyball.base_url = "http://localhost:8000"
    settings_mock.paths.players_file = tmp_data / "players.json"
    settings_mock.paths.meetups_dir = tmp_data / "meetups"

    settings_mock.paths.data_dir = tmp_data

    container = Container(settings_mock)
    # pylint: disable-next=protected-access
    container._player_repository = JsonPlayerRepository(tmp_data / "players.json")
    # pylint: disable-next=protected-access
    container._meetup_repository = JsonMeetupRepository(tmp_data / "meetups", default_capacity=10)
    return container
