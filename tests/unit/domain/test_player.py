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
        p1 = Player(id=id1, name="Luis", group="regular")
        p2 = Player(id=id1, name="Luis", group="regular")
        assert p1 == p2

    def test_create_player_with_group(self):
        player = Player.create(name="Mario", group="regular")
        assert player.name == "Mario"
        assert player.group == "regular"

    def test_create_player_with_substitute_group(self):
        player = Player.create(name="Luigi", group="substitute")
        assert player.group == "substitute"

    def test_create_player_invalid_group(self):
        with pytest.raises(ValueError):
            Player.create(name="Mario", group="invalid")

    def test_set_group(self):
        player = Player.create(name="Mario", group="regular")
        player.set_group("substitute")
        assert player.group == "substitute"
