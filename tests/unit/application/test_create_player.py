"""Tests for CreatePlayer use case."""

from unittest.mock import MagicMock

import pytest

from pyball.application.player import CreatePlayer
from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player, PlayerId


class TestCreatePlayer:
    def test_create_player_with_group(self):
        repo = MagicMock()
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Mario", group="regular")

        assert player.name == "Mario"
        assert player.group == "regular"
        repo.save.assert_called_once()

    def test_create_player_success(self):
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="Luis", group="regular")

        assert player.name == "Luis"
        assert player.group == "regular"
        repo.save.assert_called_once()

    def test_create_duplicate_player_raises(self):
        repo = MagicMock()
        repo.find_all.return_value = [Player.create(name="Luis", group="regular")]
        use_case = CreatePlayer(repo)

        with pytest.raises(PlayerAlreadyExistsError):
            use_case.execute(name="Luis", group="regular")

    def test_create_player_with_whitespace(self):
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="  Luis  ", group="regular")

        assert player.name == "Luis"
        assert player.group == "regular"
        assert len(repo.players) == 1

    def test_create_duplicate_player_raises(self):
        repo = MagicMock()
        repo.find_all.return_value = [Player.create(name="Luis", group="regular")]
        use_case = CreatePlayer(repo)

        with pytest.raises(PlayerAlreadyExistsError):
            use_case.execute(name="Luis", group="regular")

    def test_create_player_with_whitespace(self):
        repo = MagicMock()
        repo.find_all.return_value = []
        use_case = CreatePlayer(repo)

        player = use_case.execute(name="  Luis  ", group="regular")

        assert player.name == "Luis"
