"""Tests for DeletePlayer use case."""

import pytest

from pyball.application.player import DeletePlayer
from pyball.domain.player.errors import InvalidPlayerIdError, PlayerNotFoundError
from pyball.domain.player.models import Player, PlayerId


class FakePlayerRepository:
    """In-memory player repository for testing."""

    def __init__(self):
        self.players = []

    def save(self, player: Player):
        """Save or update a player."""
        existing = [p for p in self.players if p.id == player.id]
        if existing:
            self.players = [p if p.id != player.id else player for p in self.players]
        else:
            self.players.append(player)

    def find_by_id(self, player_id: PlayerId):
        """Return the player matching the given ID, or None."""
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def find_by_name(self, name: str):
        """Return the player matching the name (case-insensitive), or None."""
        for p in self.players:
            if p.name.lower() == name.lower():
                return p
        return None

    def find_all(self):
        """Return all players."""
        return list(self.players)

    def delete(self, player_id: PlayerId):
        """Remove the player with the given ID."""
        self.players = [p for p in self.players if p.id != player_id]


class TestDeletePlayer:
    """Tests for DeletePlayer use case."""

    def test_delete_player_success(self):
        """Deleting an existing player removes it from the repository."""
        repo = FakePlayerRepository()
        player = Player.create("Luis")
        repo.save(player)
        use_case = DeletePlayer(repo)

        use_case.execute(str(player.id.value))

        assert len(repo.players) == 0

    def test_delete_player_not_found(self):
        """Deleting a non-existent ID raises PlayerNotFoundError."""
        repo = FakePlayerRepository()
        use_case = DeletePlayer(repo)

        with pytest.raises(PlayerNotFoundError):
            use_case.execute(str(PlayerId.generate().value))

    def test_delete_player_invalid_id(self):
        """Passing a non-UUID string raises InvalidPlayerIdError."""
        repo = FakePlayerRepository()
        use_case = DeletePlayer(repo)

        with pytest.raises(InvalidPlayerIdError):
            use_case.execute("not-a-uuid")
