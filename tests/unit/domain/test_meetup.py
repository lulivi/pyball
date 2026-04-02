"""Tests for Meetup domain model."""

import pytest
from datetime import datetime

from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.player.models import PlayerId


class TestMeetup:
    def test_create_meetup(self):
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
        assert isinstance(meetup.id, MeetupId)
        assert meetup.date == datetime(2024, 1, 15, 20, 0)

    def test_add_regular_player(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        player_id = PlayerId.generate()
        meetup.add_regular(player_id)
        assert player_id in meetup.regulars

    def test_create_teams(self):
        meetup = Meetup.create(datetime(2024, 1, 15))
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_regular(p1)
        meetup.add_regular(p2)

        import random
        meetup.create_balanced_teams(random)

        assert meetup.teams is not None
        assert len(meetup.teams) == 2
