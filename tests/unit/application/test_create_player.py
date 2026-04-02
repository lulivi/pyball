"""Tests for CreatePlayer use case."""

import pytest

from pyball.application.player import CreatePlayer
from pyball.domain.player.errors import PlayerAlreadyExistsError
from pyball.domain.player.models import Player, PlayerId


class FakePlayerRepository:
    def __init__(self):
        self.players = []

    def save(self, player: Player):
        existing = [p for p in self.players if p.id == player.id]
        if existing:
            self.players = [p if p.id != player.id else player for p in self.players]
        else:
            self.players.append(player)

    def find_by_id(self, player_id: PlayerId):
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def find_by_name(self, name: str):
        for p in self.players:
            if p.name.lower() == name.lower():
                return p
        return None

    def find_all(self):
        return list(self.players)

    def delete(self, player_id: PlayerId):
        self.players = [p for p in self.players if p.id != player_id]


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

    def test_create_player_with_whitespace(self):
        repo = FakePlayerRepository()
        use_case = CreatePlayer(repo)

        player = use_case.execute("  Luis  ")

        assert player.name == "Luis"
