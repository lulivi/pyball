"""Tests for EditMatchResult use case."""

from datetime import datetime

import pytest

from pyball.application.meetup.edit_match_result import EditMatchResult
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import MatchResult, Meetup, PlayerId, Team
from pyball.domain.player.models import Player


class _FakeMeetupRepo:
    def __init__(self):
        self.meetups = []

    def save(self, meetup):
        """Save or update a meetup."""
        existing = [m for m in self.meetups if m.id == meetup.id]
        if existing:
            self.meetups = [m if m.id != meetup.id else meetup for m in self.meetups]
        else:
            self.meetups.append(meetup)

    def find_by_datetime(self, dt):
        """Find a meetup by datetime."""
        return next((m for m in self.meetups if m.date == dt), None)

    def find_all(self):
        """Return all meetups."""
        return list(self.meetups)


class _FakePlayerRepo:
    def __init__(self):
        self.players = []

    def find_all(self):
        """Return all players."""
        return list(self.players)


def _meetup_with_teams_and_result():
    """Return a closed meetup with two players, two teams, and an existing result."""
    meetup = Meetup.create(datetime(2026, 5, 28, 20, 0), "Campo Norte")
    p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
    p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
    meetup.teams = [Team.create("A", [p1.id]), Team.create("B", [p2.id])]
    meetup.set_result(MatchResult(score_a=1, score_b=0, events=()))
    return meetup, p1, p2


class TestEditMatchResult:
    """Tests for EditMatchResult use case."""

    def setup_method(self):
        """Set up use case with fake repositories."""
        # pylint: disable=attribute-defined-outside-init
        self.meetup_repo = _FakeMeetupRepo()
        self.player_repo = _FakePlayerRepo()
        self.use_case = EditMatchResult(self.meetup_repo, self.player_repo)

    def test_replaces_result_on_closed_meetup(self):
        """EditMatchResult overwrites the existing result on an already-closed meetup."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        events = [{"scorer": "Dani", "assistant": "Rafa", "team": "A", "timestamp": "20:15"}]
        result_meetup = self.use_case.execute("2026-05-28T20:00", events, {"A": 1, "B": 0})

        assert result_meetup.is_closed()
        assert result_meetup.result.score_a == 1
        assert result_meetup.result.score_b == 0
        assert len(result_meetup.result.events) == 1
        assert result_meetup.result.events[0].scorer_id == p1.id
        assert result_meetup.result.events[0].assistant_id == p2.id

    def test_replaces_result_without_assistant(self):
        """An event with assistant=None is stored with assistant_id=None."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        events = [{"scorer": "Dani", "assistant": None, "team": "A", "timestamp": "20:05"}]
        result_meetup = self.use_case.execute("2026-05-28T20:00", events, {"A": 1, "B": 0})

        assert result_meetup.result.events[0].assistant_id is None

    def test_raises_if_meetup_not_found(self):
        """EditMatchResult raises MeetupNotFoundError when no meetup exists on that date."""
        with pytest.raises(MeetupNotFoundError):
            self.use_case.execute("2026-05-28T20:00", [], {"A": 0, "B": 0})

    def test_raises_if_no_teams(self):
        """EditMatchResult raises ValueError when the meetup has no teams."""
        meetup = Meetup.create(datetime(2026, 5, 28, 20, 0), "Campo Norte")
        self.meetup_repo.meetups = [meetup]

        with pytest.raises(ValueError, match="Cannot set result without teams"):
            self.use_case.execute("2026-05-28T20:00", [], {"A": 0, "B": 0})

    def test_raises_if_player_not_found(self):
        """EditMatchResult raises ValueError when a scorer name cannot be fuzzy-matched."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        events = [{"scorer": "Unknown", "assistant": None, "team": "A", "timestamp": "20:00"}]
        with pytest.raises(ValueError, match="Player not found"):
            self.use_case.execute("2026-05-28T20:00", events, {"A": 1, "B": 0})

    def test_empty_events_clears_all_goals(self):
        """Passing an empty events list replaces the result with zero goals."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        result_meetup = self.use_case.execute("2026-05-28T20:00", [], {"A": 0, "B": 0})

        assert len(result_meetup.result.events) == 0
        assert result_meetup.result.score_a == 0
        assert result_meetup.result.score_b == 0

    def test_own_goal_stored_with_flag(self):
        """An event with is_own_goal=True is stored with is_own_goal=True and no assistant."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        events = [
            {
                "scorer": "Dani",
                "assistant": None,
                "team": "B",
                "timestamp": "20:15",
                "is_own_goal": True,
            }
        ]
        result_meetup = self.use_case.execute("2026-05-28T20:00", events, {"A": 0, "B": 1})

        ev = result_meetup.result.events[0]
        assert ev.is_own_goal is True
        assert ev.assistant_id is None
        assert ev.scorer_id == p1.id

    def test_own_goal_with_assistant_raises(self):
        """Passing assistant along with is_own_goal=True must raise ValueError."""
        meetup, p1, p2 = _meetup_with_teams_and_result()
        self.meetup_repo.meetups = [meetup]
        self.player_repo.players = [p1, p2]

        events = [
            {
                "scorer": "Dani",
                "assistant": "Rafa",
                "team": "B",
                "timestamp": "20:15",
                "is_own_goal": True,
            }
        ]
        with pytest.raises(ValueError, match="own goal"):
            self.use_case.execute("2026-05-28T20:00", events, {"A": 0, "B": 1})
