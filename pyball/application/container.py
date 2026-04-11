"""Dependency injection container."""

from pathlib import Path

from pyball.application.meetup import (
    AddPlayerToMeetup,
    CreateMeetup,
    CreateTeams,
    FinishMatch,
    RemovePlayerFromMeetup,
    StartMatch,
)
from pyball.application.player import CreatePlayer, DeletePlayer, RenamePlayer
from pyball.application.player.change_group import ChangePlayerGroup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure.persistence import JsonMeetupRepository, JsonPlayerRepository
from pyball.settings import load_settings


class Container:
    """Simple dependency injection container."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize the container with optional custom data directory."""
        self._settings = load_settings()
        self._player_repository: PlayerRepository | None = None
        self._meetup_repository: MeetupRepository | None = None

        if data_dir:
            self._data_dir = data_dir
        else:
            self._data_dir = self._settings.paths.data_dir

    def create_player(self) -> CreatePlayer:
        """Create a new CreatePlayer use case."""
        return CreatePlayer(self.player_repository)

    def rename_player(self) -> RenamePlayer:
        """Create a new RenamePlayer use case."""
        return RenamePlayer(self.player_repository)

    def delete_player(self) -> DeletePlayer:
        """Create a new DeletePlayer use case."""
        return DeletePlayer(self.player_repository)

    def create_meetup(self) -> CreateMeetup:
        """Create a new CreateMeetup use case."""
        return CreateMeetup(self.meetup_repository, self._settings.pyball.location)

    def change_player_group(self) -> ChangePlayerGroup:
        """Create a new ChangePlayerGroup use case."""
        return ChangePlayerGroup(self.player_repository)

    def add_player_to_meetup(self) -> AddPlayerToMeetup:
        """Create a new AddPlayerToMeetup use case."""
        return AddPlayerToMeetup(self.meetup_repository, self.player_repository)

    def remove_player_from_meetup(self) -> RemovePlayerFromMeetup:
        """Create a new RemovePlayerFromMeetup use case."""
        return RemovePlayerFromMeetup(self.meetup_repository, self.player_repository)

    def create_teams(self) -> CreateTeams:
        """Create a new CreateTeams use case."""
        return CreateTeams(self.meetup_repository)

    def start_match(self) -> StartMatch:
        """Create a new StartMatch use case."""
        return StartMatch(
            self.meetup_repository,
            self.player_repository,
            self._settings.pyball.base_url,
        )

    def finish_match(self) -> FinishMatch:
        """Create a new FinishMatch use case."""
        return FinishMatch(self.meetup_repository, self.player_repository)

    @property
    def player_repository(self) -> PlayerRepository:
        """Get the player repository, creating it if necessary."""
        if self._player_repository is None:
            self._player_repository = JsonPlayerRepository(self._settings.paths.players_file)
        return self._player_repository

    @property
    def meetup_repository(self) -> MeetupRepository:
        """Get the meetup repository, creating it if necessary."""
        if self._meetup_repository is None:
            self._meetup_repository = JsonMeetupRepository(self._settings.paths.meetups_dir)
        return self._meetup_repository
