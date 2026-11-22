"""Tests for meetup capacity and the substitute search."""

from datetime import datetime

import pytest

from pyball.domain.meetup.errors import InvalidCapacityError, MeetupFullError, SignupClosedError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import PlayerId

DATE = datetime(2026, 7, 15, 20, 0)


def _meetup(players: int, capacity: int = 10) -> Meetup:
    meetup = Meetup.create(DATE, "Campo", capacity=capacity)
    for _ in range(players):
        meetup.add_player(PlayerId.generate())
    return meetup


def test_create_rejects_capacity_below_two():
    """A meetup needs room for at least two players."""
    with pytest.raises(InvalidCapacityError):
        Meetup.create(DATE, "Campo", capacity=1)


def test_open_search_below_capacity():
    """A search opens while the roster is below capacity."""
    meetup = _meetup(9)
    meetup.open_substitute_search()
    assert meetup.substitute_search


def test_open_search_on_full_roster_fails():
    """A full roster refuses a search: raise the capacity first."""
    meetup = _meetup(10)
    with pytest.raises(MeetupFullError):
        meetup.open_substitute_search()


def test_open_search_with_teams_fails():
    """A meetup with teams has signup closed, so no search."""
    meetup = _meetup(2)
    meetup.set_teams([Team.create("A", [meetup.players[0]]), Team.create("B", [])])
    with pytest.raises(SignupClosedError):
        meetup.open_substitute_search()


def test_join_reaching_capacity_closes_search():
    """The player that fills the roster closes the search."""
    meetup = _meetup(9)
    meetup.open_substitute_search()
    meetup.add_player(PlayerId.generate())
    assert not meetup.substitute_search


def test_leave_back_to_default_closes_raised_search():
    """11 searching for 12, someone leaves: capacity returns to 10 and the search closes."""
    meetup = _meetup(11, capacity=12)
    meetup.open_substitute_search()
    meetup.remove_player(meetup.players[0], default_capacity=10)
    assert meetup.capacity == 10
    assert not meetup.substitute_search


def test_leave_below_default_keeps_searching_for_default():
    """Falling under the default keeps the search open, looking for the default."""
    meetup = _meetup(10, capacity=12)
    meetup.open_substitute_search()
    meetup.remove_player(meetup.players[0], default_capacity=10)
    assert meetup.capacity == 10
    assert meetup.substitute_search


def test_leave_above_default_keeps_raised_capacity():
    """A leave that stays above the default changes nothing."""
    meetup = _meetup(15, capacity=16)
    meetup.open_substitute_search()
    meetup.remove_player(meetup.players[0], default_capacity=12)
    assert (meetup.capacity, meetup.substitute_search) == (16, True)


def test_leave_without_search_keeps_capacity():
    """Without a search, a capacity set by hand is never lowered."""
    meetup = _meetup(11, capacity=12)
    meetup.remove_player(meetup.players[0], default_capacity=10)
    assert meetup.capacity == 12


def test_lowered_capacity_is_never_raised_back():
    """A capacity under the default (6 vs 6) stays put on leaves."""
    meetup = _meetup(11, capacity=12)
    meetup.open_substitute_search()
    meetup.remove_player(meetup.players[0], default_capacity=14)
    assert meetup.capacity == 12


def test_lowering_capacity_to_roster_closes_search():
    """Settling for the roster you have closes the search."""
    meetup = _meetup(10, capacity=12)
    meetup.open_substitute_search()
    meetup.set_capacity(10)
    assert not meetup.substitute_search


def test_set_capacity_with_teams_fails():
    """Capacity is frozen once teams exist."""
    meetup = _meetup(2)
    meetup.set_teams([Team.create("A", [meetup.players[0]]), Team.create("B", [])])
    with pytest.raises(SignupClosedError):
        meetup.set_capacity(12)


def test_set_teams_closes_search():
    """Making teams ends the search."""
    meetup = _meetup(2)
    meetup.open_substitute_search()
    meetup.set_teams([Team.create("A", [meetup.players[0]]), Team.create("B", [])])
    assert not meetup.substitute_search


def test_roster_replacement_back_to_default_closes_raised_search():
    """A roster save follows the same return-to-default rule as a leave."""
    meetup = _meetup(11, capacity=12)
    meetup.open_substitute_search()
    meetup.replace_players(meetup.players[:10], default_capacity=10)
    assert (meetup.capacity, meetup.substitute_search) == (10, False)


def test_roster_replacement_reaching_capacity_closes_search():
    """A roster save that fills the meetup closes the search."""
    meetup = _meetup(9)
    meetup.open_substitute_search()
    meetup.replace_players([*meetup.players, PlayerId.generate()], default_capacity=10)
    assert not meetup.substitute_search
