"""Tests for DeletePlayer use case."""

import pytest

from pyball.application.player import DeletePlayer
from pyball.domain.player.errors import InvalidPlayerIdError, PlayerNotFoundError
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


class TestDeletePlayer:
    def test_delete_player_success(self):
        repo = FakePlayerRepository()
        player = Player.create("Luis")
        repo.save(player)
        use_case = DeletePlayer(repo)

        use_case.execute(str(player.id.value))

        assert len(repo.players) == 0

    def test_delete_player_not_found(self):
        repo = FakePlayerRepository()
        use_case = DeletePlayer(repo)

        with pytest.raises(PlayerNotFoundError):
            use_case.execute(str(PlayerId.generate().value))

    def test_delete_player_invalid_id(self):
        repo = FakePlayerRepository()
        use_case = DeletePlayer(repo)

        with pytest.raises(InvalidPlayerIdError):
            use_case.execute("not-a-uuid")
