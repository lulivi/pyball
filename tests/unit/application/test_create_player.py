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
