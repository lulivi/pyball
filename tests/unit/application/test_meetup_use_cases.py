"""Tests for meetup use cases."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import (
    AddPlayerToMeetup,
    CreateMeetup,
    CreateTeams,
    RemovePlayerFromMeetup,
)
from pyball.application.meetup.create_teams_algorithms import RandomAlgorithm
from pyball.application.meetup.finish_match import FinishMatch
from pyball.application.meetup.get_active_meetup import GetActiveMeetup
from pyball.application.meetup.start_next_round import StartNextRound
from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupAlreadyClosedError,
    MeetupHasNoTeamsError,
    MeetupNotFoundError,
)
from pyball.domain.meetup.models import Match, MatchResult, Meetup, MeetupId, PlayerId, Team
from pyball.domain.player.models import Player


class FakeMeetupRepository:
    """In-memory meetup repository for testing."""

    def __init__(self):
        self.meetups = []

    def save(self, meetup: Meetup):
        """Save or update a meetup."""
        existing = [m for m in self.meetups if m.id == meetup.id]
        if existing:
            self.meetups = [m if m.id != meetup.id else meetup for m in self.meetups]
        else:
            self.meetups.append(meetup)

    def find_by_id(self, meetup_id: MeetupId):
        """Return the meetup matching the given ID, or None."""
        for m in self.meetups:
            if m.id == meetup_id:
                return m
        return None

    def find_by_datetime(self, meetup_date):
        """Return the meetup on the given datetime, or None."""
        for m in self.meetups:
            if m.date == meetup_date:
                return m
        return None

    def find_all(self):
        """Return all meetups."""
        return list(self.meetups)

    def delete(self, meetup_id: MeetupId):
        """Remove the meetup with the given ID."""
        self.meetups = [m for m in self.meetups if m.id != meetup_id]

    def delete_by_datetime(self, meetup_date) -> None:
        """Remove the meetup at the given datetime."""
        self.meetups = [m for m in self.meetups if m.date != meetup_date]


class FakePlayerRepository:
    """In-memory player repository for testing."""

    def __init__(self):
        self.players = []

    def save(self, player: Player):
        """Save or update a player."""
        existing = [p for p in self.players if p.id == player.id]
        if existing:
            self.players = [p if p.id != player.id else player for p in self.players]
        else:
            self.players.append(player)

    def find_by_id(self, player_id: PlayerId):
        """Return the player matching the given ID, or None."""
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def find_by_name(self, name: str):
        """Return the player matching the name (case-insensitive), or None."""
        for p in self.players:
            if p.name.lower() == name.lower():
                return p
        return None

    def find_all(self):
        """Return all players."""
        return list(self.players)

    def delete(self, player_id: PlayerId):
        """Remove the player with the given ID."""
        self.players = [p for p in self.players if p.id != player_id]


class TestAddPlayerToMeetup:
    """Tests for AddPlayerToMeetup use case."""

    def test_add_player_to_meetup_fuzzy(self):
        """Adding a player by fuzzy name match inserts their ID into the meetup."""
        player_repo = MagicMock()
        player = Player.create(name="Mario", group="regular")
        player_repo.find_all.return_value = [player]

        meetup_repo = MagicMock()
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        meetup_repo.find_by_datetime.return_value = meetup

        use_case = AddPlayerToMeetup(meetup_repo, player_repo)
        use_case.execute(datetime(2024, 3, 20, 20, 0), "Mario")

        assert player.id in meetup.players

    def test_add_player_clears_existing_teams(self):
        """Adding a player to a meetup that already has teams clears the teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])
        meetup_repo.save(meetup)

        player = Player.create(name="Mario", group="regular")
        player_repo = FakePlayerRepository()
        player_repo.save(player)

        use_case = AddPlayerToMeetup(meetup_repo, player_repo)
        result = use_case.execute(datetime(2024, 3, 20, 20, 0), "Mario")

        assert result.teams is None

    def test_add_player_when_no_teams_leaves_teams_as_none(self):
        """Adding a player to a meetup without teams leaves teams as None."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 3, 20, 20, 0), location="Parque Central")
        meetup_repo.save(meetup)

        player = Player.create(name="Mario", group="regular")
        player_repo = FakePlayerRepository()
        player_repo.save(player)

        use_case = AddPlayerToMeetup(meetup_repo, player_repo)
        result = use_case.execute(datetime(2024, 3, 20, 20, 0), "Mario")

        assert result.teams is None

    def test_add_player_raises_when_meetup_not_found(self):
        """execute raises MeetupNotFoundError if no meetup exists on that date."""
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        use_case = AddPlayerToMeetup(meetup_repo, player_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2099, 1, 1, 20, 0), "Mario")


class TestRemovePlayerFromMeetup:
    """Tests for RemovePlayerFromMeetup use case."""

    def test_remove_player_success(self):
        """Removing a player by name removes their ID from the meetup."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player = Player.create(name="Mario", group="regular")
        meetup.add_player(player.id)
        meetup_repo.save(meetup)

        player_repo = FakePlayerRepository()
        player_repo.save(player)

        use_case = RemovePlayerFromMeetup(meetup_repo, player_repo)
        use_case.execute(datetime(2024, 1, 15, 20, 0), "Mario")

        assert player.id not in meetup.players

    def test_remove_player_meetup_not_found(self):
        """Removing a player when the meetup does not exist raises MeetupNotFoundError."""
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        use_case = RemovePlayerFromMeetup(meetup_repo, player_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2024, 1, 15, 20, 0), "Mario")

    def test_remove_player_clears_existing_teams(self):
        """Removing a player from a meetup that already has teams clears the teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player = Player.create(name="Mario", group="regular")
        extra = PlayerId.generate()
        meetup.add_player(player.id)
        meetup.add_player(extra)
        meetup.set_teams([Team.create("A", [player.id]), Team.create("B", [extra])])
        meetup_repo.save(meetup)

        player_repo = FakePlayerRepository()
        player_repo.save(player)

        result = RemovePlayerFromMeetup(meetup_repo, player_repo).execute(
            datetime(2024, 1, 15, 20, 0), "Mario"
        )

        assert result.teams is None

    def test_remove_player_without_teams_leaves_teams_as_none(self):
        """Removing a player from a meetup without teams leaves teams as None."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player = Player.create(name="Mario", group="regular")
        meetup.add_player(player.id)
        meetup_repo.save(meetup)

        player_repo = FakePlayerRepository()
        player_repo.save(player)

        result = RemovePlayerFromMeetup(meetup_repo, player_repo).execute(
            datetime(2024, 1, 15, 20, 0), "Mario"
        )

        assert result.teams is None


class TestCreateTeams:
    """Tests for CreateTeams use case."""

    def test_create_teams_success(self):
        """Creating teams for a meetup with 2 players produces two teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo, RandomAlgorithm())

        result = use_case.execute(datetime(2024, 1, 15, 20, 0))

        assert result.teams is not None
        assert len(result.teams) == 2

    def test_create_teams_meetup_not_found(self):
        """Creating teams when the meetup does not exist raises MeetupNotFoundError."""
        meetup_repo = FakeMeetupRepository()
        use_case = CreateTeams(meetup_repo, RandomAlgorithm())

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2024, 1, 15, 20, 0))

    def test_create_teams_not_enough_players(self):
        """Creating teams with fewer than 2 players raises ValueError."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo, RandomAlgorithm())

        with pytest.raises(ValueError, match="Need at least 2"):
            use_case.execute(datetime(2024, 1, 15, 20, 0))

    def test_create_teams_all_players_assigned(self):
        """All meetup players appear in exactly one team after create_teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player_ids = [PlayerId.generate() for _ in range(6)]
        for pid in player_ids:
            meetup.add_player(pid)
        meetup_repo.save(meetup)

        result = CreateTeams(meetup_repo, RandomAlgorithm()).execute(datetime(2024, 1, 15, 20, 0))

        all_assigned = list(result.teams[0].players) + list(result.teams[1].players)
        assert sorted(str(p.value) for p in all_assigned) == sorted(
            str(p.value) for p in player_ids
        )

    def test_create_teams_produces_varied_results(self):
        """Repeated calls on the same meetup produce more than one distinct assignment."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        for _ in range(6):
            meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo, RandomAlgorithm())

        compositions = set()
        for _ in range(30):
            result = use_case.execute(datetime(2024, 1, 15, 20, 0))
            compositions.add(frozenset(result.teams[0].players))

        assert len(compositions) > 1

    def test_create_teams_with_history_uses_all_meetups(self):
        """CreateTeams loads all finished meetups and assigns all current players to teams."""
        meetup_repo = FakeMeetupRepository()

        # Create two historical finished meetups
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        past_meetup = Meetup.create(date=datetime(2024, 10, 1, 20, 0), location="Parque Central")
        past_meetup.add_player(p1)
        past_meetup.add_player(p2)
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        past_meetup.set_teams([team_a, team_b])
        past_meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
        meetup_repo.save(past_meetup)

        # Create the current meetup with the same players
        current = Meetup.create(date=datetime(2024, 11, 15, 20, 0), location="Parque Central")
        current.add_player(p1)
        current.add_player(p2)
        meetup_repo.save(current)

        result = CreateTeams(meetup_repo, RandomAlgorithm()).execute(datetime(2024, 11, 15, 20, 0))

        assert result.teams is not None
        assert len(result.teams) == 2
        all_assigned = list(result.teams[0].players) + list(result.teams[1].players)
        assert set(all_assigned) == {p1, p2}

    def test_create_teams_with_team_count_three(self):
        """team_count=3 produces three teams named A, B, C covering all players."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        player_ids = [PlayerId.generate() for _ in range(9)]
        for pid in player_ids:
            meetup.add_player(pid)
        meetup_repo.save(meetup)

        result = CreateTeams(meetup_repo, RandomAlgorithm()).execute(
            datetime(2024, 1, 15, 20, 0), team_count=3
        )

        assert result.teams is not None
        assert len(result.teams) == 3
        assert [t.name for t in result.teams] == ["A", "B", "C"]
        all_assigned = [pid for team in result.teams for pid in team.players]
        assert sorted(str(p.value) for p in all_assigned) == sorted(
            str(p.value) for p in player_ids
        )

    def test_create_teams_team_count_rejects_invalid_value(self):
        """team_count outside {2, 3} raises ValueError."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)

        with pytest.raises(ValueError, match="team_count must be 2 or 3"):
            CreateTeams(meetup_repo, RandomAlgorithm()).execute(
                datetime(2024, 1, 15, 20, 0), team_count=4
            )


class TestCreateMeetup:
    """Tests for CreateMeetup use case."""

    def test_create_meetup_with_default_location(self):
        """Creating a meetup without a location uses the default."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0))

        assert meetup.location == "Parque Central"
        assert meetup.date == datetime(2024, 3, 20, 20, 0)

    def test_create_meetup_with_custom_location(self):
        """Creating a meetup with a custom location overrides the default."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0), location="Estadio Norte")

        assert meetup.location == "Estadio Norte"

    def test_create_meetup_duplicate_date_raises_error(self):
        """Creating a meetup on an already-used date raises DuplicateMeetupError."""
        existing_meetup = Meetup.create(
            date=datetime(2024, 3, 20, 20, 0), location="Parque Central"
        )
        repo = MagicMock()
        repo.find_by_datetime.return_value = existing_meetup
        use_case = CreateMeetup(repo, default_location="Parque Central")

        with pytest.raises(DuplicateMeetupError, match="Meetup already exists"):
            use_case.execute(date=datetime(2024, 3, 20, 20, 0))

    def test_create_meetup_saves_meetup(self):
        """Creating a meetup persists it via the repository."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0))

        repo.save.assert_called_once_with(meetup)


class TestStartNextRound:
    """Tests for StartNextRound use case."""

    def setup_method(self):
        """Set up a fresh meetup repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.meetup_repo = FakeMeetupRepository()

    def test_raises_when_meetup_missing(self):
        """StartNextRound raises MeetupNotFoundError when no meetup exists for the date."""
        with pytest.raises(MeetupNotFoundError):
            StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))

    def test_raises_when_no_teams(self):
        """StartNextRound raises MeetupHasNoTeamsError when the meetup has no teams yet."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.meetup_repo.save(meetup)
        with pytest.raises(MeetupHasNoTeamsError):
            StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))

    def test_classic_two_teams_creates_the_one_match(self):
        """With 2 teams, the first (only) match is created between them."""
        self._meetup_with_teams(count=2)
        result = StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))
        assert len(result.matches) == 1
        assert set(result.matches[0].teams_playing) == set(result.teams)
        assert result.matches[0].result is None

    def test_calling_again_does_not_duplicate_the_pending_match(self):
        """Calling execute again while a match is already pending is a no-op."""
        self._meetup_with_teams(count=2)
        StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))
        result = StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))
        assert len(result.matches) == 1

    def test_triangular_creates_first_random_pairing(self):
        """With 3 teams, the first match pairs 2 of the 3 teams, chosen at random."""
        self._meetup_with_teams(count=3)
        result = StartNextRound(self.meetup_repo).execute(datetime(2026, 4, 12, 20, 0))
        assert len(result.matches) == 1
        playing = set(result.matches[0].teams_playing)
        assert playing.issubset(set(result.teams))
        assert len(playing) == 2

    def _meetup_with_teams(self, count=2):
        """Create and save a meetup with `count` empty teams."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        names = ["A", "B", "C"][:count]
        meetup.teams = [Team.create(n, []) for n in names]
        self.meetup_repo.save(meetup)
        return meetup


class TestFinishMatch:
    """Tests for FinishMatch use case."""

    def setup_method(self):
        """Set up FinishMatch use case with fake repositories."""
        # pylint: disable=attribute-defined-outside-init
        self.meetup_repo = FakeMeetupRepository()
        self.player_repo = FakePlayerRepository()
        self.use_case = FinishMatch(self.meetup_repo, self.player_repo)

    def _meetup_with_teams(self):
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
        p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
        self.player_repo.players.extend([p1, p2])
        team_a, team_b = Team.create("A", [p1.id]), Team.create("B", [p2.id])
        meetup.teams = [team_a, team_b]
        meetup.add_match(Match(teams_playing=(team_a, team_b)))
        self.meetup_repo.save(meetup)
        return meetup, p1, p2

    def test_saves_result_with_resolved_player_ids(self):
        """FinishMatch resolves player names and persists MatchResult."""
        _, p1, p2 = self._meetup_with_teams()

        events = [
            {
                "scorer": "Dani",
                "assistant": "Rafa",
                "team": "A",
                "timestamp": "20:15",
            }
        ]
        self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})

        saved = self.meetup_repo.find_by_datetime(datetime(2026, 4, 12, 20, 0))
        assert saved is not None
        assert saved.is_closed()
        result = saved.matches[0].result
        assert result.score_a == 1
        assert result.score_b == 0
        assert len(result.events) == 1
        assert result.events[0].scorer_id == p1.id
        assert result.events[0].assistant_id == p2.id

    def test_goal_without_assistant(self):
        """An event with assistant=None stores assistant_id=None."""
        _, _, _ = self._meetup_with_teams()

        events = [
            {
                "scorer": "Dani",
                "assistant": None,
                "team": "A",
                "timestamp": "20:05",
            }
        ]
        self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})

        saved = self.meetup_repo.find_by_datetime(datetime(2026, 4, 12, 20, 0))
        assert saved.matches[0].result.events[0].assistant_id is None

    def test_two_teams_closes_meetup_automatically(self):
        """With 2 teams, finishing the one match closes the meetup, as before."""
        self._meetup_with_teams()
        self.use_case.execute("2026-04-12 20:00", [], {"A": 1, "B": 0})
        saved = self.meetup_repo.find_by_datetime(datetime(2026, 4, 12, 20, 0))
        assert saved.is_closed()
        assert len(saved.matches) == 1
        assert saved.matches[0].result.score_a == 1

    def test_three_teams_appends_next_round_instead_of_closing(self):
        """With 3 teams, finishing a match appends the next computed round and stays open."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
        p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
        p3 = Player(id=PlayerId.generate(), name="Nico", group="regular")
        self.player_repo.players.extend([p1, p2, p3])
        team_a, team_b, team_c = (
            Team.create("A", [p1.id]),
            Team.create("B", [p2.id]),
            Team.create("C", [p3.id]),
        )
        meetup.teams = [team_a, team_b, team_c]
        meetup.add_match(Match(teams_playing=(team_a, team_b)))
        self.meetup_repo.save(meetup)

        result = self.use_case.execute("2026-04-12 20:00", [], {"A": 2, "B": 0})

        assert not result.is_closed()
        assert len(result.matches) == 2
        assert result.matches[0].result.score_a == 2
        assert result.matches[1].result is None
        assert set(result.matches[1].teams_playing) == {team_a, team_c}

    def test_raises_if_meetup_not_found(self):
        """FinishMatch raises MeetupNotFoundError for unknown dates."""
        with pytest.raises(MeetupNotFoundError):
            self.use_case.execute("2026-04-12 20:00", [], {"A": 0, "B": 0})

    def test_raises_if_already_closed(self):
        """FinishMatch raises MeetupAlreadyClosedError if the meetup is already closed."""
        meetup, _, _ = self._meetup_with_teams()
        meetup.record_result(MatchResult(score_a=1, score_b=0, events=()))
        meetup.close()
        self.meetup_repo.save(meetup)

        with pytest.raises(MeetupAlreadyClosedError):
            self.use_case.execute("2026-04-12 20:00", [], {"A": 1, "B": 0})

    def test_raises_if_no_pending_match(self):
        """FinishMatch raises ValueError if there is no pending match to record."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        meetup.teams = [Team.create("A", []), Team.create("B", [])]
        self.meetup_repo.save(meetup)

        with pytest.raises(ValueError, match="No pending match"):
            self.use_case.execute("2026-04-12 20:00", [], {"A": 0, "B": 0})

    def test_raises_if_player_not_found(self):
        """FinishMatch raises ValueError if a player name cannot be resolved."""
        self._meetup_with_teams()

        events = [
            {
                "scorer": "Unknown",
                "assistant": None,
                "team": "A",
                "timestamp": "20:00",
            }
        ]
        with pytest.raises(ValueError, match="Player not found"):
            self.use_case.execute("2026-04-12 20:00", events, {"A": 1, "B": 0})


class TestGetActiveMeetup:
    """Tests for GetActiveMeetup use case."""

    def setup_method(self):
        """Set up a fresh meetup repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.meetup_repo = FakeMeetupRepository()

    def test_returns_most_recent_active_meetup(self):
        """Returns the meetup with the latest date when multiple active ones exist."""
        older = Meetup.create(datetime(2026, 5, 1, 20, 0), "Campo")
        newer = Meetup.create(datetime(2026, 6, 1, 20, 0), "Campo")
        self.meetup_repo.save(older)
        self.meetup_repo.save(newer)
        assert GetActiveMeetup(self.meetup_repo).execute() == newer

    def test_ignores_closed_meetups(self):
        """A closed meetup is not returned."""
        closed = Meetup.create(datetime(2026, 6, 5, 20, 0), "Campo")
        closed.close()
        self.meetup_repo.save(closed)
        active = Meetup.create(datetime(2026, 5, 1, 20, 0), "Campo")
        self.meetup_repo.save(active)
        assert GetActiveMeetup(self.meetup_repo).execute() == active

    def test_raises_if_no_active_meetup(self):
        """Raises MeetupNotFoundError when no meetup with result=None exists."""
        with pytest.raises(MeetupNotFoundError):
            GetActiveMeetup(self.meetup_repo).execute()

    def test_require_teams_excludes_meetups_without_teams(self):
        """require_teams=True skips meetups that have no teams yet."""
        with_teams = Meetup.create(datetime(2026, 5, 1, 20, 0), "Campo")
        with_teams.teams = [Team.create("A", []), Team.create("B", [])]
        self.meetup_repo.save(with_teams)
        without_teams = Meetup.create(datetime(2026, 6, 2, 20, 0), "Campo")
        self.meetup_repo.save(without_teams)
        # without_teams is newer but has no teams; require_teams must return with_teams
        assert GetActiveMeetup(self.meetup_repo).execute(require_teams=True) == with_teams

    def test_require_teams_raises_if_no_active_meetup_with_teams(self):
        """require_teams=True raises when active meetups exist but none have teams."""
        meetup = Meetup.create(datetime(2026, 6, 1, 20, 0), "Campo")
        self.meetup_repo.save(meetup)
        with pytest.raises(MeetupNotFoundError):
            GetActiveMeetup(self.meetup_repo).execute(require_teams=True)
