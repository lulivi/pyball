"""Tests for meetup use cases."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import (
    AddPlayerToMeetup,
    CreateMeetup,
    CreateTeams,
    DuplicateMeetupError,
    RemovePlayerFromMeetup,
)
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, MeetupId, PlayerId
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

    def find_by_date(self, meetup_date):
        """Return the meetup on the given date, or None."""
        for m in self.meetups:
            if m.date.date() == meetup_date:
                return m
        return None

    def find_all(self):
        """Return all meetups."""
        return list(self.meetups)

    def delete(self, meetup_id: MeetupId):
        """Remove the meetup with the given ID."""
        self.meetups = [m for m in self.meetups if m.id != meetup_id]


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
        meetup_repo.find_by_date.return_value = meetup

        use_case = AddPlayerToMeetup(meetup_repo, player_repo)
        use_case.execute("2024-03-20 20:00", "Mario")

        assert player.id in meetup.players


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
        use_case.execute("2024-01-15 20:00", "Mario")

        assert player.id not in meetup.players

    def test_remove_player_meetup_not_found(self):
        """Removing a player when the meetup does not exist raises MeetupNotFoundError."""
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        use_case = RemovePlayerFromMeetup(meetup_repo, player_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute("2024-01-15 20:00", "Mario")


class TestCreateTeams:
    """Tests for CreateTeams use case."""

    def test_create_teams_success(self):
        """Creating teams for a meetup with 2 players produces two teams."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        result = use_case.execute("2024-01-15 20:00")

        assert result.teams is not None
        assert len(result.teams) == 2

    def test_create_teams_meetup_not_found(self):
        """Creating teams when the meetup does not exist raises MeetupNotFoundError."""
        meetup_repo = FakeMeetupRepository()
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute("2024-01-15 20:00")

    def test_create_teams_not_enough_players(self):
        """Creating teams with fewer than 2 players raises ValueError."""
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(date=datetime(2024, 1, 15, 20, 0), location="Parque Central")
        meetup.add_player(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(ValueError, match="Need at least 2"):
            use_case.execute("2024-01-15 20:00")


class TestCreateMeetup:
    """Tests for CreateMeetup use case."""

    def test_create_meetup_with_default_location(self):
        """Creating a meetup without a location uses the default."""
        repo = MagicMock()
        repo.find_by_date.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0))

        assert meetup.location == "Parque Central"
        assert meetup.date == datetime(2024, 3, 20, 20, 0)

    def test_create_meetup_with_custom_location(self):
        """Creating a meetup with a custom location overrides the default."""
        repo = MagicMock()
        repo.find_by_date.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0), location="Estadio Norte")

        assert meetup.location == "Estadio Norte"

    def test_create_meetup_duplicate_date_raises_error(self):
        """Creating a meetup on an already-used date raises DuplicateMeetupError."""
        existing_meetup = Meetup.create(
            date=datetime(2024, 3, 20, 20, 0), location="Parque Central"
        )
        repo = MagicMock()
        repo.find_by_date.return_value = existing_meetup
        use_case = CreateMeetup(repo, default_location="Parque Central")

        with pytest.raises(DuplicateMeetupError, match="Meetup already exists"):
            use_case.execute(date=datetime(2024, 3, 20, 20, 0))

    def test_create_meetup_saves_meetup(self):
        """Creating a meetup persists it via the repository."""
        repo = MagicMock()
        repo.find_by_date.return_value = None
        use_case = CreateMeetup(repo, default_location="Parque Central")

        meetup = use_case.execute(date=datetime(2024, 3, 20, 20, 0))

        repo.save.assert_called_once_with(meetup)


class TestStartMatch:
    """Tests for StartMatch use case."""

    def setup_method(self):
        # pylint: disable=attribute-defined-outside-init
        from pyball.application.meetup.start_match import StartMatch

        self.meetup_repo = FakeMeetupRepository()
        self.player_repo = FakePlayerRepository()
        self.use_case = StartMatch(self.meetup_repo, self.player_repo, "http://pyball:8000")

    def _add_players_and_teams(self, meetup):
        from pyball.domain.meetup.models import Team

        p1 = Player(id=PlayerId.generate(), name="Dani", group="regular")
        p2 = Player(id=PlayerId.generate(), name="Rafa", group="regular")
        self.player_repo.players.append(p1)
        self.player_repo.players.append(p2)
        meetup.teams = [Team.create("A", [p1.id]), Team.create("B", [p2.id])]
        self.meetup_repo.save(meetup)
        return p1, p2

    def test_returns_url_with_teams_and_date(self):
        """StartMatch returns a URL containing date and team names."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1, p2 = self._add_players_and_teams(meetup)

        url = self.use_case.execute("2026-04-12 20:00")

        assert "2026-04-12T20%3A00" in url or "2026-04-12T20:00" in url
        assert "Dani" in url
        assert "Rafa" in url
        assert url.startswith("http://pyball:8000")

    def test_raises_if_meetup_not_found(self):
        """StartMatch raises MeetupNotFoundError if no meetup exists on that date."""
        with pytest.raises(MeetupNotFoundError):
            self.use_case.execute("2026-04-12 20:00")

    def test_raises_if_no_teams(self):
        """StartMatch raises MeetupHasNoTeamsError if teams have not been created."""
        from pyball.application.meetup.start_match import MeetupHasNoTeamsError

        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.meetup_repo.save(meetup)

        with pytest.raises(MeetupHasNoTeamsError):
            self.use_case.execute("2026-04-12 20:00")
