# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Dependency injection container."""

from pyball.application.meetup import (
    AddPlayerToMeetup,
    AssignTeamsById,
    ComputeStats,
    CreateMeetup,
    CreateTeams,
    CreateTeamsManually,
    EditMatchResult,
    FinishMatch,
    FormatMatchSummary,
    GetActiveMeetup,
    ParseCallup,
    RemovePlayerFromMeetup,
    SetMeetupPlayers,
    StartMatch,
    UpdateMeetupDate,
    UpdateMeetupLocation,
)
from pyball.application.meetup.create_teams_algorithms import (
    DEFAULT_ALGORITHM,
    BalancedAlgorithm,
    RandomAlgorithm,
    TeamAssignmentAlgorithm,
)
from pyball.application.player import CreatePlayer, DeletePlayer, RenamePlayer
from pyball.application.player.change_group import ChangePlayerGroup
from pyball.domain.meetup.errors import UnknownAlgorithmError
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository
from pyball.infrastructure.http.links import MatchLinkBuilder
from pyball.infrastructure.persistence import (
    JsonMeetupRepository,
    JsonPlayerRepository,
    LegacyStats,
)
from pyball.settings import AppSettings


class Container:  # pylint: disable=too-many-public-methods
    """Simple dependency injection container."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize the container with application settings."""
        self._settings = settings
        self._player_repository: PlayerRepository | None = None
        self._meetup_repository: MeetupRepository | None = None
        self._legacy_stats: LegacyStats | None = None

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

    def create_teams(self, algo_name: str | None = None) -> CreateTeams:
        """Create a new CreateTeams use case with the specified or default algorithm."""
        registry = self._algorithm_registry()
        name = algo_name or DEFAULT_ALGORITHM
        if name not in registry:
            raise UnknownAlgorithmError(name, list(registry.keys()))
        return CreateTeams(self.meetup_repository, registry[name])

    def create_teams_manually(self) -> CreateTeamsManually:
        """Create a new CreateTeamsManually use case."""
        return CreateTeamsManually(self.meetup_repository, self.player_repository)

    def assign_teams_by_id(self) -> AssignTeamsById:
        """Create a new AssignTeamsById use case."""
        return AssignTeamsById(self.meetup_repository)

    def start_match(self) -> StartMatch:
        """Create a new StartMatch use case."""
        return StartMatch(self.meetup_repository)

    def match_link_builder(self) -> MatchLinkBuilder:
        """Create the web match-link builder for this instance."""
        return MatchLinkBuilder(self.base_url, self._settings.pyball.match_token)

    def get_active_meetup(self) -> GetActiveMeetup:
        """Create a new GetActiveMeetup use case."""
        return GetActiveMeetup(self.meetup_repository)

    def finish_match(self) -> FinishMatch:
        """Create a new FinishMatch use case."""
        return FinishMatch(self.meetup_repository, self.player_repository)

    def edit_match_result(self) -> EditMatchResult:
        """Create a new EditMatchResult use case."""
        return EditMatchResult(self.meetup_repository, self.player_repository)

    def compute_stats(self) -> ComputeStats:
        """Create a new ComputeStats use case."""
        return ComputeStats(self.meetup_repository, self.player_repository, self.legacy_stats)

    def format_match_summary(self) -> FormatMatchSummary:
        """Create a new FormatMatchSummary use case."""
        return FormatMatchSummary()

    def update_meetup_date(self) -> UpdateMeetupDate:
        """Create a new UpdateMeetupDate use case."""
        return UpdateMeetupDate(self.meetup_repository)

    def update_meetup_location(self) -> UpdateMeetupLocation:
        """Create a new UpdateMeetupLocation use case."""
        return UpdateMeetupLocation(self.meetup_repository)

    def set_meetup_players(self) -> SetMeetupPlayers:
        """Create a new SetMeetupPlayers use case."""
        return SetMeetupPlayers(self.meetup_repository, self._settings.pyball.location)

    def parse_callup(self) -> ParseCallup:
        """Create a new ParseCallup use case."""
        return ParseCallup(self.player_repository, self.default_hour)

    @property
    def team_colors(self) -> tuple[str, str]:
        """Return the configured team color names."""
        return self._settings.pyball.team_colors

    @property
    def team_emojis(self) -> tuple[str, str]:
        """Return the configured team emojis."""
        return self._settings.pyball.team_emojis

    @property
    def team_hex_bg(self) -> tuple[str, str]:
        """Return the configured team background hex colors."""
        return self._settings.pyball.team_hex_bg

    @property
    def team_hex_text(self) -> tuple[str, str]:
        """Return the configured team text hex colors."""
        return self._settings.pyball.team_hex_text

    @property
    def base_url(self) -> str:
        """Return the configured instance URL (used for match links)."""
        return self._settings.pyball.base_url

    @property
    def default_hour(self) -> str:
        """Return the configured default match hour as 'HH:MM'."""
        return self._settings.pyball.default_hour

    @property
    def name(self) -> str:
        """Return the configured instance name."""
        return self._settings.pyball.name

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

    @property
    def legacy_stats(self) -> LegacyStats:
        """Get the legacy stats, loading from file if necessary."""
        if self._legacy_stats is None:
            legacy_path = self._settings.paths.data_dir / "legacy_stats.json"
            self._legacy_stats = LegacyStats.from_file(str(legacy_path))
        return self._legacy_stats

    def _algorithm_registry(self) -> dict[str, TeamAssignmentAlgorithm]:
        """Build the algorithm registry with all available algorithms."""
        return {
            "balanceado": BalancedAlgorithm(self.legacy_stats),
            "random": RandomAlgorithm(),
        }
