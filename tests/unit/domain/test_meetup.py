"""Tests for Meetup domain model."""

from datetime import datetime, time

import pytest

from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
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


class TestGoalEvent:
    """Tests for GoalEvent value object."""

    def test_goal_event_with_assistant(self):
        """A goal event stores scorer, optional assistant, team and timestamp."""
        scorer = PlayerId.generate()
        assistant = PlayerId.generate()
        ts = time(20, 15)
        event = GoalEvent(scorer_id=scorer, assistant_id=assistant, team="A", timestamp=ts)
        assert event.scorer_id == scorer
        assert event.assistant_id == assistant
        assert event.team == "A"
        assert event.timestamp == ts

    def test_goal_event_without_assistant(self):
        """A goal event may have no assistant."""
        scorer = PlayerId.generate()
        event = GoalEvent(scorer_id=scorer, assistant_id=None, team="B", timestamp=time(20, 5))
        assert event.assistant_id is None


class TestMatchResult:
    """Tests for MatchResult value object."""

    def test_match_result_stores_score_and_events(self):
        """MatchResult holds the final score and goal events."""
        scorer = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer,
            assistant_id=None,
            team="A",
            timestamp=time(20, 5),
        )
        result = MatchResult(score_a=1, score_b=0, events=(event,))
        assert result.score_a == 1
        assert result.score_b == 0
        assert len(result.events) == 1


class TestSetTeams:
    """Tests for Meetup.set_teams."""

    def test_set_teams_assigns_two_teams(self):
        """set_teams stores two teams on the meetup."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        meetup.set_teams(teams)
        assert meetup.teams == teams

    def test_set_teams_requires_exactly_two(self):
        """set_teams raises ValueError when not given exactly two teams."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        with pytest.raises(ValueError, match="Exactly two teams required"):
            meetup.set_teams([Team.create("A", [])])


class TestClearTeams:
    """Tests for Meetup.clear_teams."""

    def test_clear_teams_sets_teams_to_none(self):
        """clear_teams removes any previously assigned teams."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        assert meetup.teams is not None

        meetup.clear_teams()

        assert meetup.teams is None


class TestMeetupResult:
    """Tests for Meetup.set_result and is_closed."""

    def _meetup_with_teams(self):
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        return meetup

    def test_is_closed_false_by_default(self):
        """A new meetup is not closed."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        assert not meetup.is_closed()

    def test_set_result_closes_meetup(self):
        """Setting a result marks the meetup as closed."""
        meetup = self._meetup_with_teams()
        result = MatchResult(score_a=3, score_b=2, events=())
        meetup.set_result(result)
        assert meetup.is_closed()
        assert meetup.result == result

    def test_set_result_requires_teams(self):
        """set_result raises ValueError if teams have not been created."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        result = MatchResult(score_a=1, score_b=0, events=())
        with pytest.raises(ValueError, match="Cannot set result without teams"):
            meetup.set_result(result)
