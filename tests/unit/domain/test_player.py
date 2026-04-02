"""Tests for Player domain model."""

import pytest

from pyball.domain.player.models import Player, PlayerId


class TestPlayer:
    def test_create_player_with_valid_name(self):
        player = Player.create("Luis")
        assert player.name == "Luis"
        assert isinstance(player.id, PlayerId)

    def test_create_player_with_empty_name_raises(self):
        with pytest.raises(ValueError):
            Player.create("")

    def test_rename_player(self):
        player = Player.create("Luis")
        player.rename("Carlos")
        assert player.name == "Carlos"

    def test_player_equality(self):
        id1 = PlayerId.generate()
        p1 = Player(id=id1, name="Luis")
        p2 = Player(id=id1, name="Luis")
        assert p1 == p2
