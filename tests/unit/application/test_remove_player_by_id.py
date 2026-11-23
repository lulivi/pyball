# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Tests for RemovePlayerFromMeetupById use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.remove_player_by_id import RemovePlayerFromMeetupById
from pyball.domain.meetup.errors import (
    MeetupNotFoundError,
    PlayerNotInMeetupError,
    SignupClosedError,
)
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import Player


def _player(name: str) -> Player:
    return Player.create(name=name, group="regular")


def _meetup(*players: Player) -> Meetup:
    m = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
    for p in players:
        m.add_player(p.id)
    return m


class TestRemovePlayerFromMeetupById:
    """Tests for RemovePlayerFromMeetupById use case."""

    def test_removes_player_from_open_meetup(self):
        """Removing a player by ID removes their ID from the meetup."""
        p1 = _player("Juan")
        meetup = _meetup(p1)
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        result = RemovePlayerFromMeetupById(repo, default_capacity=10).execute(
            datetime(2026, 5, 6, 20, 0), p1.id
        )

        assert p1.id not in result.players
        repo.save.assert_called_once_with(meetup)

    def test_raises_meetup_not_found(self):
        """execute raises MeetupNotFoundError if no meetup exists on that date."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None

        with pytest.raises(MeetupNotFoundError):
            RemovePlayerFromMeetupById(repo, default_capacity=10).execute(
                datetime(2026, 5, 6, 20, 0), _player("Juan").id
            )

    def test_raises_signup_closed_once_teams_assigned(self):
        """Removing a player once teams are assigned raises SignupClosedError."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        meetup.set_teams([Team.create("A", [p1.id]), Team.create("B", [p2.id])])
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(SignupClosedError):
            RemovePlayerFromMeetupById(repo, default_capacity=10).execute(
                datetime(2026, 5, 6, 20, 0), p1.id
            )

    def test_raises_player_not_in_meetup(self):
        """Removing a player who never joined raises PlayerNotInMeetupError."""
        meetup = _meetup()
        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup

        with pytest.raises(PlayerNotInMeetupError):
            RemovePlayerFromMeetupById(repo, default_capacity=10).execute(
                datetime(2026, 5, 6, 20, 0), _player("Juan").id
            )
