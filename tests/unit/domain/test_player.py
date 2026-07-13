"""Tests for Player domain model."""

import pytest

from pyball.domain.player.models import Player, PlayerId


class TestPlayer:
    """Tests for Player domain model."""

    def test_create_player_with_valid_name(self):
        """Creating a player with a valid name assigns the name and generates an ID."""
        player = Player.create("Luis")
        assert player.name == "Luis"
        assert isinstance(player.id, PlayerId)

    def test_create_player_with_empty_name_raises(self):
        """Creating a player with an empty name raises ValueError."""
        with pytest.raises(ValueError):
            Player.create("")

    def test_rename_player(self):
        """Renaming a player updates the name in place."""
        player = Player.create("Luis")
        player.rename("Carlos")
        assert player.name == "Carlos"

    def test_player_equality(self):
        """Two players with the same ID are considered equal."""
        id1 = PlayerId.generate()
        p1 = Player(id=id1, name="Luis", group="regular")
        p2 = Player(id=id1, name="Luis", group="regular")
        assert p1 == p2

    def test_create_player_with_group(self):
        """Creating a player with an explicit group assigns it."""
        player = Player.create(name="Mario", group="regular")
        assert player.name == "Mario"
        assert player.group == "regular"

    def test_create_player_with_substitute_group(self):
        """Creating a player with the substitute group assigns it."""
        player = Player.create(name="Luigi", group="substitute")
        assert player.group == "substitute"

    def test_create_player_invalid_group(self):
        """Creating a player with an unknown group raises ValueError."""
        with pytest.raises(ValueError):
            Player.create(name="Mario", group="invalid")

    def test_set_group(self):
        """Setting a player's group updates it in place."""
        player = Player.create(name="Mario", group="regular")
        player.set_group("substitute")
        assert player.group == "substitute"

    def test_create_player_with_position(self):
        """Creating a player with a position assigns it."""
        player = Player.create(name="Mario", group="regular", position="portero")
        assert player.position == "portero"

    def test_create_player_defaults_to_no_position(self):
        """A player created without a position has position=None."""
        player = Player.create(name="Mario")
        assert player.position is None

    def test_create_player_invalid_position_raises(self):
        """Creating a player with an unknown position raises ValueError."""
        with pytest.raises(ValueError):
            Player.create(name="Mario", position="lateral")

    def test_set_position(self):
        """Setting a player's position updates it in place."""
        player = Player.create(name="Mario")
        player.set_position("defensa")
        assert player.position == "defensa"

    def test_set_position_to_none_clears_it(self):
        """Setting a player's position to None clears a previously set position."""
        player = Player.create(name="Mario", position="delantero")
        player.set_position(None)
        assert player.position is None

    def test_set_position_invalid_raises(self):
        """Setting an unknown position raises ValueError."""
        player = Player.create(name="Mario")
        with pytest.raises(ValueError):
            player.set_position("lateral")
