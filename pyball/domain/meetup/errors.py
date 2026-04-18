"""Meetup domain errors."""

from pyball.exceptions import MeetupError


class MeetupNotFoundError(MeetupError):
    """Raised when a meetup is not found."""

    def __init__(self, meetup_id: str):
        """Initialize with the missing meetup ID."""
        self.meetup_id = meetup_id
        super().__init__(f"Meetup with id '{meetup_id}' not found")


class PlayerNotInMeetupError(MeetupError):
    """Raised when a player is not in the meetup."""

    def __init__(self, player_id: str):
        """Initialize with the absent player ID."""
        self.player_id = player_id
        super().__init__(f"Player '{player_id}' is not in this meetup")


class InvalidMeetupIdError(MeetupError):
    """Raised when a meetup ID is not a valid UUID."""

    def __init__(self, meetup_id: str):
        """Initialize with the invalid meetup ID."""
        self.meetup_id = meetup_id
        super().__init__(f"Invalid meetup ID format: '{meetup_id}'")
