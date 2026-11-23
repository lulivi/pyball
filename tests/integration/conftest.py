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
