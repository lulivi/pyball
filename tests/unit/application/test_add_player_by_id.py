"""Tests for AddPlayerToMeetupById use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.add_player_by_id import AddPlayerToMeetupById
from pyball.domain.meetup.errors import MeetupNotFoundError, SignupClosedError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player


def _player(name: str) -> Player:
    return Player.create(name=name, group="regular")


def _meetup(*players: Player) -> Meetup:
    m = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
    for p in players:
        m.add_player(p.id)
    return m


class TestAddPlayerToMeetupById:
    """Tests for AddPlayerToMeetupById use case."""

    def test_adds_player_to_open_meetup(self):
        """Adding a player by ID inserts their ID into the meetup."""
        p1 = _player("Juan")
        meetup = _meetup()
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        result = AddPlayerToMeetupById(repo).execute(datetime(2026, 5, 6, 20, 0), p1.id)

        assert p1.id in result.players
        repo.save.assert_called_once_with(meetup)

    def test_raises_meetup_not_found(self):
        """execute raises MeetupNotFoundError if no meetup exists on that date."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None

        with pytest.raises(MeetupNotFoundError):
            AddPlayerToMeetupById(repo).execute(datetime(2026, 5, 6, 20, 0), _player("Juan").id)

    def test_raises_signup_closed_once_teams_assigned(self):
        """Adding a player once teams are assigned raises SignupClosedError."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        meetup.set_teams([Team.create("A", [p1.id]), Team.create("B", [p2.id])])
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(SignupClosedError):
            AddPlayerToMeetupById(repo).execute(datetime(2026, 5, 6, 20, 0), _player("Ana").id)

    def test_adding_already_joined_player_is_idempotent(self):
        """Adding a player already in the meetup does not duplicate their ID."""
        p1 = _player("Juan")
        meetup = _meetup(p1)
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        result = AddPlayerToMeetupById(repo).execute(datetime(2026, 5, 6, 20, 0), p1.id)

        assert result.players.count(p1.id) == 1
