"""Tests for meetup use cases."""

from datetime import datetime

import pytest

from pyball.application.meetup import AddPlayerToMeetup, CreateTeams, RemovePlayerFromMeetup
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, MeetupId, PlayerId
from pyball.domain.player.errors import PlayerNotFoundError
from pyball.domain.player.models import Player


class FakeMeetupRepository:
    def __init__(self):
        self.meetups = []

    def save(self, meetup: Meetup):
        existing = [m for m in self.meetups if m.id == meetup.id]
        if existing:
            self.meetups = [m if m.id != meetup.id else meetup for m in self.meetups]
        else:
            self.meetups.append(meetup)

    def find_by_id(self, meetup_id: MeetupId):
        for m in self.meetups:
            if m.id == meetup_id:
                return m
        return None

    def find_by_date(self, meetup_date):
        for m in self.meetups:
            if m.date.date() == meetup_date:
                return m
        return None

    def find_all(self):
        return list(self.meetups)

    def delete(self, meetup_id: MeetupId):
        self.meetups = [m for m in self.meetups if m.id != meetup_id]


class FakePlayerRepository:
    def __init__(self):
        self.players = []

    def save(self, player: Player):
        existing = [p for p in self.players if p.id == player.id]
        if existing:
            self.players = [p if p.id != player.id else player for p in self.players]
        else:
            self.players.append(player)

    def find_by_id(self, player_id: PlayerId):
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def find_by_name(self, name: str):
        for p in self.players:
            if p.name.lower() == name.lower():
                return p
        return None

    def find_all(self):
        return list(self.players)

    def delete(self, player_id: PlayerId):
        self.players = [p for p in self.players if p.id != player_id]


class TestAddPlayerToMeetup:
    def test_add_regular_player_success(self):
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        player = Player.create("Luis")
        meetup_repo.save(meetup)
        player_repo.save(player)
        use_case = AddPlayerToMeetup(meetup_repo, player_repo)

        result = use_case.execute(str(meetup.id.value), str(player.id.value), "regular")

        assert player.id in result.regulars

    def test_add_substitute_player_success(self):
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        player = Player.create("Luis")
        meetup_repo.save(meetup)
        player_repo.save(player)
        use_case = AddPlayerToMeetup(meetup_repo, player_repo)

        result = use_case.execute(str(meetup.id.value), str(player.id.value), "substitute")

        assert player.id in result.substitutes

    def test_add_player_meetup_not_found(self):
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        player = Player.create("Luis")
        player_repo.save(player)
        use_case = AddPlayerToMeetup(meetup_repo, player_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(str(MeetupId.generate().value), str(player.id.value))

    def test_add_player_player_not_found(self):
        meetup_repo = FakeMeetupRepository()
        player_repo = FakePlayerRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        meetup_repo.save(meetup)
        use_case = AddPlayerToMeetup(meetup_repo, player_repo)

        with pytest.raises(PlayerNotFoundError):
            use_case.execute(str(meetup.id.value), str(PlayerId.generate().value))


class TestRemovePlayerFromMeetup:
    def test_remove_player_success(self):
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        player_id = PlayerId.generate()
        meetup.add_regular(player_id)
        meetup_repo.save(meetup)
        use_case = RemovePlayerFromMeetup(meetup_repo)

        use_case.execute(str(meetup.id.value), str(player_id.value))

        assert player_id not in meetup.regulars

    def test_remove_player_meetup_not_found(self):
        meetup_repo = FakeMeetupRepository()
        use_case = RemovePlayerFromMeetup(meetup_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(str(MeetupId.generate().value), str(PlayerId.generate().value))


class TestCreateTeams:
    def test_create_teams_success(self):
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        meetup.add_regular(PlayerId.generate())
        meetup.add_regular(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        result = use_case.execute(str(meetup.id.value))

        assert result.teams is not None
        assert len(result.teams) == 2

    def test_create_teams_meetup_not_found(self):
        meetup_repo = FakeMeetupRepository()
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(str(MeetupId.generate().value))

    def test_create_teams_not_enough_players(self):
        meetup_repo = FakeMeetupRepository()
        meetup = Meetup.create(datetime(2024, 1, 15))
        meetup.add_regular(PlayerId.generate())
        meetup_repo.save(meetup)
        use_case = CreateTeams(meetup_repo)

        with pytest.raises(ValueError, match="Need at least 2"):
            use_case.execute(str(meetup.id.value))
