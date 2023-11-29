import uuid


class PlayerNotFoundError(Exception):
    """The player was not found in the repository."""


class PlayerUuidAlreadyExistsError(Exception):
    """There is a player with the same UUID in the repository."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player id `{id}` is already in use"
        super().__init__(self.message)


class PlayerNameAlreadyInUseError(Exception):
    """The name of the player is already in use."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f'The player name "{name}" is already in use'
        super().__init__(self.message)
