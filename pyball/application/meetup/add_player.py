"""Add player to meetup use case."""

from datetime import datetime

from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId
from pyball.domain.player.repository import PlayerRepository


class AddPlayerToMeetup:
    """Use case for adding a player to a meetup."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ):
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(self, date_str: str, player_name: str) -> Meetup:
        """Add player to meetup by date string and fuzzy name match."""
        try:
            meetup_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError("Invalid date format. Use: YYYY-MM-DD HH:MM")

        all_meetups = self.meetup_repository.find_all()
        meetup = None
        for m in all_meetups:
            if m.date == meetup_date:
                meetup = m
                break

        if not meetup:
            raise MeetupNotFoundError(date_str)

        all_players = self.player_repository.find_all()
        match = fuzzy_match_player(player_name, all_players)
        player_id = match.player_id

        meetup.add_player(player_id)
        self.meetup_repository.save(meetup)
        return meetup
