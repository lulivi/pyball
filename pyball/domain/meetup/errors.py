"""Meetup domain errors."""


class MeetupNotFoundError(Exception):
    """Raised when a meetup is not found."""

    def __init__(self, meetup_id: str):
        self.meetup_id = meetup_id
        super().__init__(f"Meetup with id '{meetup_id}' not found")


class PlayerNotInMeetupError(Exception):
    """Raised when a player is not in the meetup."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Player '{player_id}' is not in this meetup")
