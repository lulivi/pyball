"""Remove player from meetup use case."""

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import MeetupId
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class RemovePlayerFromMeetup:
    """Use case for removing a player from a meetup."""

    def __init__(self, meetup_repository: MeetupRepository):
        self.meetup_repository = meetup_repository

    def execute(self, meetup_id: str, player_id: str) -> None:
        meetup = self.meetup_repository.find_by_id(MeetupId.from_string(meetup_id))
        if not meetup:
            raise MeetupNotFoundError(meetup_id)

        player_id_obj = PlayerId.from_string(player_id)
        meetup.remove_player(player_id_obj)
        self.meetup_repository.save(meetup)