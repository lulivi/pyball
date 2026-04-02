"""Tests for RenamePlayer use case."""

import pytest

from pyball.application.player import RenamePlayer
from pyball.domain.player.errors import InvalidPlayerIdError, NameAlreadyTakenError, PlayerNotFoundError
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


class TestRenamePlayer:
    def test_rename_player_success(self):
        repo = FakePlayerRepository()
        player = Player.create("Luis")
        repo.save(player)
        use_case = RenamePlayer(repo)

        renamed = use_case.execute(str(player.id.value), "Carlos")

        assert renamed.name == "Carlos"

    def test_rename_player_not_found(self):
        repo = FakePlayerRepository()
        use_case = RenamePlayer(repo)

        with pytest.raises(PlayerNotFoundError):
            use_case.execute(str(PlayerId.generate().value), "Carlos")

    def test_rename_player_invalid_id(self):
        repo = FakePlayerRepository()
        use_case = RenamePlayer(repo)

        with pytest.raises(InvalidPlayerIdError):
            use_case.execute("not-a-uuid", "Carlos")

    def test_rename_player_to_existing_name(self):
        repo = FakePlayerRepository()
        player1 = Player.create("Luis")
        player2 = Player.create("Carlos")
        repo.save(player1)
        repo.save(player2)
        use_case = RenamePlayer(repo)

        with pytest.raises(NameAlreadyTakenError):
            use_case.execute(str(player1.id.value), "Carlos")

    def test_rename_player_to_same_name(self):
        repo = FakePlayerRepository()
        player = Player.create("Luis")
        repo.save(player)
        use_case = RenamePlayer(repo)

        renamed = use_case.execute(str(player.id.value), "Luis")

        assert renamed.name == "Luis"
