"""Player domain errors."""

from pyball.exceptions import PlayerError


class PlayerNotFoundError(PlayerError):
    """Raised when a player is not found."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Player with id '{player_id}' not found")


class PlayerAlreadyExistsError(PlayerError):
    """Raised when trying to create a player that already exists."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Player with name '{name}' already exists")


class InvalidPlayerIdError(PlayerError):
    """Raised when a player ID is not a valid UUID."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Invalid player ID format: '{player_id}'")


class NameAlreadyTakenError(PlayerError):
    """Raised when trying to rename a player to an existing name."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Name '{name}' is already taken by another player")
