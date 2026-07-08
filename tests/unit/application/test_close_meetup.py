"""Tests for CloseMeetup use case."""

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from pyball.application.meetup.close_meetup import CloseMeetup
from pyball.domain.meetup.errors import MeetupAlreadyClosedError, MeetupNotFoundError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId

if TYPE_CHECKING:
    from pyball.domain.meetup.repository import MeetupRepository


class FakeMeetupRepository:
    """Minimal in-memory meetup repository for this test."""

    def __init__(self) -> None:
        """Initialize the repository."""
        self.meetups: list[Meetup] = []

    def save(self, meetup: Meetup) -> None:
        """Save a meetup."""
        self.meetups = [m for m in self.meetups if m.id != meetup.id] + [meetup]

    def find_by_datetime(self, meetup_date: datetime) -> Meetup | None:
        """Find a meetup by date."""
        return next((m for m in self.meetups if m.date == meetup_date), None)


class TestCloseMeetup:
    """Tests for CloseMeetup."""

    def test_closes_meetup_with_a_finished_current_round(self) -> None:
        """Test that a meetup with a finished round can be closed."""
        repo: MeetupRepository = FakeMeetupRepository()  # type: ignore
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        team_a, team_b, team_c = (
            Team.create("A", [PlayerId.generate()]),
            Team.create("B", [PlayerId.generate()]),
            Team.create("C", [PlayerId.generate()]),
        )
        meetup.teams = [team_a, team_b, team_c]
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
        repo.save(meetup)

        result = CloseMeetup(repo).execute(datetime(2026, 4, 12, 20, 0))

        assert result.is_closed()
        assert len(result.matches) == 1
        assert result.matches[0].result is not None

    def test_closing_removes_a_trailing_dangling_pending_match(self) -> None:
        """Test that a trailing pending match (no result) is removed on close."""
        repo: MeetupRepository = FakeMeetupRepository()  # type: ignore
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        team_a, team_b, team_c = (
            Team.create("A", [PlayerId.generate()]),
            Team.create("B", [PlayerId.generate()]),
            Team.create("C", [PlayerId.generate()]),
        )
        meetup.teams = [team_a, team_b, team_c]
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
        meetup.add_match(Match(teams_playing=(team_b, team_c), result=None))
        repo.save(meetup)

        result = CloseMeetup(repo).execute(datetime(2026, 4, 12, 20, 0))

        assert result.is_closed()
        assert len(result.matches) == 1
        assert result.matches[0].result is not None

    def test_raises_if_meetup_not_found(self) -> None:
        """Test that closing a nonexistent meetup raises MeetupNotFoundError."""
        repo: MeetupRepository = FakeMeetupRepository()  # type: ignore
        with pytest.raises(MeetupNotFoundError):
            CloseMeetup(repo).execute(datetime(2026, 4, 12, 20, 0))

    def test_raises_if_already_closed(self) -> None:
        """Test that closing an already-closed meetup raises MeetupAlreadyClosedError."""
        repo: MeetupRepository = FakeMeetupRepository()  # type: ignore
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        meetup.close()
        repo.save(meetup)

        with pytest.raises(MeetupAlreadyClosedError):
            CloseMeetup(repo).execute(datetime(2026, 4, 12, 20, 0))
