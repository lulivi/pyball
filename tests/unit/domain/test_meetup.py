"""Tests for Meetup domain model."""

from datetime import datetime

import pytest

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import PlayerId


class TestMeetup:
    """Tests for Meetup domain model."""

    def test_create_meetup_with_location(self):
        """Creating a meetup sets the location and starts with no players."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        assert meetup.location == "Parque Central"
        assert not meetup.players

    def test_meetup_add_player(self):
        """Adding a player inserts their ID into the players list."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        player_id = PlayerId.generate()
        meetup.add_player(player_id)
        assert player_id in meetup.players

    def test_meetup_remove_player(self):
        """Removing a player deletes their ID from the players list."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        player_id = PlayerId.generate()
        meetup.add_player(player_id)
        meetup.remove_player(player_id)
        assert player_id not in meetup.players

    def test_meetup_location_required(self):
        """Creating a meetup with an empty location raises ValueError."""
        with pytest.raises(ValueError):
            Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="")
