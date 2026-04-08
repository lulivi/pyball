"""Add player to meetup use case."""

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, MeetupId
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.errors import PlayerNotFoundError
from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository

REGULAR = "regular"
SUBSTITUTE = "substitute"


class AddPlayerToMeetup:
    """Use case for adding a player to a meetup."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ):
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self, meetup_id: str, player_id: str, role: str = "regular") -> Meetup:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            raise MeetupNotFoundError(meetup_id)

        parsed_player_id = PlayerId.from_string(player_id)
        player = self.player_repository.find_by_id(parsed_player_id)
        if not player:
            raise PlayerNotFoundError(player_id)

        if role == SUBSTITUTE:
            meetup.add_substitute(parsed_player_id)
        else:
            meetup.add_regular(parsed_player_id)

        self.meetup_repository.save(meetup)
        return meetup
