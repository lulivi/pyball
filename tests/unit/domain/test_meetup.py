"""Tests for Meetup domain model."""

from datetime import datetime

import pytest

from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.player.models import PlayerId


class TestMeetup:
    def test_create_meetup_with_location(self):
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        assert meetup.location == "Parque Central"
        assert meetup.players == []

    def test_meetup_add_player(self):
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        player_id = PlayerId.generate()
        meetup.add_player(player_id)
        assert player_id in meetup.players

    def test_meetup_remove_player(self):
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        player_id = PlayerId.generate()
        meetup.add_player(player_id)
        meetup.remove_player(player_id)
        assert player_id not in meetup.players

    def test_meetup_location_required(self):
        with pytest.raises(ValueError):
            Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="")
