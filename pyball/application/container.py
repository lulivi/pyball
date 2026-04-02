"""Dependency injection container."""

from pathlib import Path

from pyball.application.meetup import (
    CreateMeetup,
    AddPlayerToMeetup,
    RemovePlayerFromMeetup,
    CreateTeams,
)
from pyball.application.player import (
    CreatePlayer,
    RenamePlayer,
    DeletePlayer,
)
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure import JsonPlayerRepository, JsonMeetupRepository


class Container:
    """Simple dependency injection container."""

    _player_repository: PlayerRepository | None = None
    _meetup_repository: MeetupRepository | None = None

    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            from pyball.settings import load_settings
            self._data_dir = load_settings().paths.data_dir
        else:
            self._data_dir = data_dir

    @property
    def player_repository(self) -> PlayerRepository:
        if self._player_repository is None:
            from pyball.settings import load_settings
            settings = load_settings()
            self._player_repository = JsonPlayerRepository(settings.paths.players_file)
        return self._player_repository

    @property
    def meetup_repository(self) -> MeetupRepository:
        if self._meetup_repository is None:
            from pyball.settings import load_settings
            settings = load_settings()
            self._meetup_repository = JsonMeetupRepository(settings.paths.meetups_dir)
        return self._meetup_repository

    def create_player(self) -> CreatePlayer:
        return CreatePlayer(self.player_repository)

    def rename_player(self) -> RenamePlayer:
        return RenamePlayer(self.player_repository)

    def delete_player(self) -> DeletePlayer:
        return DeletePlayer(self.player_repository)

    def create_meetup(self) -> CreateMeetup:
        return CreateMeetup(self.meetup_repository)

    def add_player_to_meetup(self) -> AddPlayerToMeetup:
        return AddPlayerToMeetup(self.meetup_repository, self.player_repository)

    def remove_player_from_meetup(self) -> RemovePlayerFromMeetup:
        return RemovePlayerFromMeetup(self.meetup_repository)

    def create_teams(self) -> CreateTeams:
        return CreateTeams(self.meetup_repository)