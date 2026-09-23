"""Tests for Meetup domain model."""

from datetime import datetime, time

import pytest

from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, Team
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

    def test_set_location_changes_location(self):
        """set_location replaces the meetup location."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        meetup.set_location("Parque Sur")
        assert meetup.location == "Parque Sur"

    def test_set_location_strips_whitespace(self):
        """set_location strips surrounding whitespace."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        meetup.set_location("  Parque Sur  ")
        assert meetup.location == "Parque Sur"

    def test_set_location_raises_on_empty_string(self):
        """set_location raises ValueError for empty or blank location."""
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        with pytest.raises(ValueError):
            meetup.set_location("")

    def test_set_date_changes_date(self):
        """set_date replaces the meetup date."""
        original = datetime(2024, 3, 20, 20, 0)
        new_date = datetime(2024, 3, 27, 20, 0)
        meetup = Meetup.create(date=original, location="Parque Central")
        meetup.set_date(new_date)
        assert meetup.date == new_date


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

    def test_winner_index_returns_zero_when_team_a_wins(self):
        """winner_index() returns 0 when score_a is higher."""
        result = MatchResult(score_a=2, score_b=1, events=())
        assert result.winner_index() == 0

    def test_winner_index_returns_one_when_team_b_wins(self):
        """winner_index() returns 1 when score_b is higher."""
        result = MatchResult(score_a=0, score_b=3, events=())
        assert result.winner_index() == 1

    def test_winner_index_returns_none_on_draw(self):
        """winner_index() returns None when scores are equal."""
        result = MatchResult(score_a=2, score_b=2, events=())
        assert result.winner_index() is None


class TestSetTeams:
    """Tests for Meetup.set_teams."""

    def test_set_teams_assigns_two_teams(self):
        """set_teams stores two teams on the meetup."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        teams = [Team.create("A", [p1]), Team.create("B", [p2])]
        meetup.set_teams(teams)
        assert meetup.teams == teams


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


class TestMatches:
    """Tests for Meetup.matches / current_match / record_result / close."""

    def _meetup_with_teams(self, count=2):
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        names = ["A", "B", "C"][:count]
        meetup.teams = [Team.create(n, [PlayerId.generate()]) for n in names]
        return meetup

    def test_is_closed_false_by_default(self):
        """A new meetup is not closed."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        assert not meetup.is_closed()

    def test_add_match_appends_to_matches(self):
        """add_match appends the given match to the matches list."""
        meetup = self._meetup_with_teams()
        match = Match(teams_playing=(meetup.teams[0], meetup.teams[1]))
        meetup.add_match(match)
        assert meetup.matches == [match]

    def test_current_match_returns_pending_match(self):
        """current_match returns the last match when it has no result."""
        meetup = self._meetup_with_teams()
        match = Match(teams_playing=(meetup.teams[0], meetup.teams[1]))
        meetup.add_match(match)
        assert meetup.current_match() is match

    def test_current_match_returns_none_when_last_match_has_result(self):
        """current_match returns None when the last match already has a result."""
        meetup = self._meetup_with_teams()
        match = Match(
            teams_playing=(meetup.teams[0], meetup.teams[1]),
            result=MatchResult(score_a=1, score_b=0, events=()),
        )
        meetup.add_match(match)
        assert meetup.current_match() is None

    def test_current_match_returns_none_when_no_matches(self):
        """current_match returns None when there are no matches yet."""
        meetup = self._meetup_with_teams()
        assert meetup.current_match() is None

    def test_record_result_sets_result_on_current_match(self):
        """record_result attaches the result to the current pending match."""
        meetup = self._meetup_with_teams()
        match = Match(teams_playing=(meetup.teams[0], meetup.teams[1]))
        meetup.add_match(match)
        result = MatchResult(score_a=2, score_b=1, events=())
        meetup.record_result(result)
        assert meetup.matches[0].result == result

    def test_record_result_raises_without_pending_match(self):
        """record_result raises ValueError when there is no pending match."""
        meetup = self._meetup_with_teams()
        with pytest.raises(ValueError, match="No pending match"):
            meetup.record_result(MatchResult(score_a=1, score_b=0, events=()))

    def test_close_marks_meetup_closed(self):
        """close marks the meetup as closed."""
        meetup = self._meetup_with_teams()
        meetup.close()
        assert meetup.is_closed()


class TestSetTeamsThreeWay:
    """Tests for Meetup.set_teams accepting 3 teams (triangular)."""

    def test_set_teams_accepts_three_teams(self):
        """set_teams stores three teams on the meetup."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        teams = [Team.create(n, [PlayerId.generate()]) for n in ("A", "B", "C")]
        meetup.set_teams(teams)
        assert meetup.teams == teams

    def test_set_teams_rejects_one_team(self):
        """set_teams raises ValueError when given only one team."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        with pytest.raises(ValueError, match="Two or three teams required"):
            meetup.set_teams([Team.create("A", [])])

    def test_set_teams_rejects_four_teams(self):
        """set_teams raises ValueError when given four teams."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        teams = [Team.create(n, []) for n in ("A", "B", "C", "D")]
        with pytest.raises(ValueError, match="Two or three teams required"):
            meetup.set_teams(teams)


class TestClearTeamsResetsMatches:
    """clear_teams must also wipe matches/closed — they reference the old teams."""

    def test_clear_teams_resets_matches_and_closed(self):
        """clear_teams resets matches to empty and closed to False."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        teams = [Team.create("A", []), Team.create("B", [])]
        meetup.set_teams(teams)
        meetup.add_match(Match(teams_playing=(teams[0], teams[1])))
        meetup.close()

        meetup.clear_teams()

        assert meetup.teams is None
        assert not meetup.matches
        assert not meetup.is_closed()


class TestSignupOpenAndRecordedResults:
    """Tests for Meetup.is_signup_open / has_recorded_results."""

    def test_is_signup_open_true_when_no_teams(self):
        """is_signup_open returns True while teams is None."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        assert meetup.is_signup_open()

    def test_is_signup_open_false_once_teams_assigned(self):
        """is_signup_open returns False once teams are set."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        assert not meetup.is_signup_open()

    def test_has_recorded_results_false_with_only_pending_matches(self):
        """has_recorded_results is False when no match has a result yet."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        meetup.add_match(Match(teams_playing=(meetup.teams[0], meetup.teams[1])))
        assert not meetup.has_recorded_results()

    def test_has_recorded_results_true_once_a_match_has_a_result(self):
        """has_recorded_results is True once any match has a result."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        meetup.add_match(
            Match(
                teams_playing=(meetup.teams[0], meetup.teams[1]),
                result=MatchResult(score_a=1, score_b=0, events=()),
            )
        )
        assert meetup.has_recorded_results()


class TestGoalEventOwnGoal:
    """GoalEvent own-goal field."""

    def test_default_is_own_goal_is_false(self):
        """GoalEvent.is_own_goal defaults to False."""
        pid = PlayerId.generate()
        event = GoalEvent(
            scorer_id=pid,
            assistant_id=None,
            team="A",
            timestamp=time(20, 5),
        )
        assert event.is_own_goal is False

    def test_can_create_own_goal_event(self):
        """GoalEvent can be created with is_own_goal=True."""
        pid = PlayerId.generate()
        event = GoalEvent(
            scorer_id=pid,
            assistant_id=None,
            team="B",
            timestamp=time(20, 5),
            is_own_goal=True,
        )
        assert event.is_own_goal is True

    def test_own_goal_event_is_frozen(self):
        """GoalEvent is frozen — is_own_goal cannot be reassigned."""
        pid = PlayerId.generate()
        event = GoalEvent(
            scorer_id=pid,
            assistant_id=None,
            team="B",
            timestamp=time(20, 5),
            is_own_goal=True,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.is_own_goal = False  # type: ignore[misc]


class TestTeam:
    """Tests for the Team value object's goalkeeper field."""

    def test_create_without_goalkeeper_defaults_to_none(self):
        """A team created without a goalkeeper has goalkeeper=None."""
        p1 = PlayerId.generate()
        team = Team.create("A", [p1])
        assert team.goalkeeper is None

    def test_create_with_goalkeeper(self):
        """A team created with a goalkeeper who is one of its players is accepted."""
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        team = Team.create("A", [p1, p2], goalkeeper=p1)
        assert team.goalkeeper == p1

    def test_create_with_goalkeeper_not_in_players_raises(self):
        """A goalkeeper who isn't one of the team's players raises ValueError."""
        p1, outsider = PlayerId.generate(), PlayerId.generate()
        with pytest.raises(ValueError):
            Team.create("A", [p1], goalkeeper=outsider)
