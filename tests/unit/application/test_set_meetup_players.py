"""Tests for the SetMeetupPlayers use case."""

from datetime import datetime

import pytest

from pyball.application.meetup.set_meetup_players import SetMeetupPlayers
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupLockedError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, Team
from pyball.domain.player.errors import InvalidPlayerIdError
from pyball.domain.player.models import PlayerId

DATE = datetime(2026, 6, 17, 20, 0)


class FakeMeetupRepository:
    """In-memory meetup repository."""

    def __init__(self):
        """Initialize the fake repository."""
        self.meetups = {}
        self.saved = []

    def save(self, meetup):
        """Save a meetup to the in-memory store."""
        self.meetups[meetup.date] = meetup
        self.saved.append(meetup)

    def find_by_datetime(self, meetup_date):
        """Return the meetup at the given date, or None."""
        return self.meetups.get(meetup_date)


def _use_case(repo):
    """Build the use case with Parque Central as default location."""
    return SetMeetupPlayers(repo, default_location="Parque Central")


def _pid():
    """Generate a fresh player ID string."""
    return str(PlayerId.generate().value)


def test_creates_meetup_with_players_when_missing():
    """New meetup is created with the given players when none exists."""
    repo = FakeMeetupRepository()
    ids = [_pid(), _pid()]

    meetup = _use_case(repo).execute(DATE, ids)

    assert meetup.date == DATE
    assert meetup.location == "Parque Central"
    assert [str(p.value) for p in meetup.players] == ids
    assert repo.saved == [meetup]


def test_resets_players_and_teams_on_existing_open_meetup():
    """Existing open meetup has its players replaced and teams cleared."""
    repo = FakeMeetupRepository()
    existing = Meetup.create(date=DATE, location="Old")
    old_player = PlayerId.generate()
    existing.add_player(old_player)
    existing.set_teams([Team.create("A", [old_player]), Team.create("B", [PlayerId.generate()])])
    repo.save(existing)
    new_ids = [_pid()]

    meetup = _use_case(repo).execute(DATE, new_ids)

    assert meetup is existing
    assert [str(p.value) for p in meetup.players] == new_ids
    assert meetup.teams is None
    assert meetup.location == "Old"


def test_raises_when_meetup_is_closed():
    """MeetupAlreadyClosedError is raised for a meetup that has a result."""
    repo = FakeMeetupRepository()
    closed = Meetup.create(date=DATE, location="Old")
    pid_a, pid_b = PlayerId.generate(), PlayerId.generate()
    team_a, team_b = Team.create("A", [pid_a]), Team.create("B", [pid_b])
    closed.set_teams([team_a, team_b])
    closed.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, ())))
    closed.close()
    repo.save(closed)

    with pytest.raises(MeetupAlreadyClosedError):
        _use_case(repo).execute(DATE, [_pid()])


def test_raises_when_meetup_is_locked():
    """MeetupLockedError is raised when the existing meetup is locked."""
    repo = FakeMeetupRepository()
    existing = Meetup.create(date=DATE, location="Old")
    pid_a, pid_b = PlayerId.generate(), PlayerId.generate()
    existing.add_player(pid_a)
    existing.set_teams([Team.create("A", [pid_a]), Team.create("B", [pid_b])])
    existing.lock()
    repo.save(existing)

    with pytest.raises(MeetupLockedError):
        _use_case(repo).execute(DATE, [_pid()])

    assert existing.players == [pid_a]


def test_invalid_player_id_leaves_repository_untouched():
    """InvalidPlayerIdError is raised and no meetup is saved for a bad UUID."""
    repo = FakeMeetupRepository()

    with pytest.raises(InvalidPlayerIdError):
        _use_case(repo).execute(DATE, ["not-a-uuid"])

    assert not repo.meetups
