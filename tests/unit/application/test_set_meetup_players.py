"""Tests for the SetMeetupPlayers use case."""

import logging
from datetime import datetime

import pytest

from pyball.application.meetup.set_meetup_players import SetMeetupPlayers
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupHasRecordedResultsError
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
    return SetMeetupPlayers(repo, default_location="Parque Central", default_capacity=10)


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


def test_raises_when_meetup_has_recorded_results():
    """MeetupHasRecordedResultsError is raised once the existing meetup has a result."""
    repo = FakeMeetupRepository()
    existing = Meetup.create(date=DATE, location="Old")
    pid_a, pid_b = PlayerId.generate(), PlayerId.generate()
    existing.add_player(pid_a)
    existing.set_teams([Team.create("A", [pid_a]), Team.create("B", [pid_b])])
    existing.add_match(
        Match(
            teams_playing=(existing.teams[0], existing.teams[1]),
            result=MatchResult(score_a=1, score_b=0, events=()),
        )
    )
    repo.save(existing)

    with pytest.raises(MeetupHasRecordedResultsError):
        _use_case(repo).execute(DATE, [_pid()])

    assert existing.players == [pid_a]


def test_execute_logs_creation_when_meetup_is_new(caplog):
    """Creating a new meetup via SetMeetupPlayers logs a creation INFO record."""
    repo = FakeMeetupRepository()
    with caplog.at_level(logging.INFO, logger="pyball.application.meetup.set_meetup_players"):
        _use_case(repo).execute(DATE, [])
    recs = [r for r in caplog.records if r.name == "pyball.application.meetup.set_meetup_players"]
    assert len(recs) == 1 and recs[0].levelno == logging.INFO
    assert "created" in recs[0].getMessage().lower()


def test_execute_logs_roster_set_when_meetup_exists(caplog):
    """Resetting an existing meetup's roster logs a roster-set DEBUG record."""
    repo = FakeMeetupRepository()
    _use_case(repo).execute(DATE, [])
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="pyball.application.meetup.set_meetup_players"):
        _use_case(repo).execute(DATE, [])
    recs = [r for r in caplog.records if r.name == "pyball.application.meetup.set_meetup_players"]
    assert len(recs) == 1 and recs[0].levelno == logging.DEBUG
    assert "roster set" in recs[0].getMessage().lower()


def test_invalid_player_id_leaves_repository_untouched():
    """InvalidPlayerIdError is raised and no meetup is saved for a bad UUID."""
    repo = FakeMeetupRepository()

    with pytest.raises(InvalidPlayerIdError):
        _use_case(repo).execute(DATE, ["not-a-uuid"])

    assert not repo.meetups
