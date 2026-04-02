"""Tests for CreatePlayer use case."""

import pytest

from pyball.application.player import CreatePlayer
from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player


class FakePlayerRepository:
    def __init__(self):
        self.players = []

    def save(self, player: Player):
        self.players.append(player)

    def find_by_name(self, name: str):
        for p in self.players:
            if p.name == name:
                return p
        return None


class TestCreatePlayer:
    def test_create_player_success(self):
        repo = FakePlayerRepository()
        use_case = CreatePlayer(repo)

        player = use_case.execute("Luis")

        assert player.name == "Luis"
        assert len(repo.players) == 1

    def test_create_duplicate_player_raises(self):
        repo = FakePlayerRepository()
        repo.save(Player.create("Luis"))
        use_case = CreatePlayer(repo)

        with pytest.raises(PlayerAlreadyExistsError):
            use_case.execute("Luis")
