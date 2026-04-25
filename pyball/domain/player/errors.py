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
"""Player domain errors."""

from pyball.exceptions import PlayerError


class PlayerNotFoundError(PlayerError):
    """Raised when a player is not found."""

    def __init__(self, player_id: str):
        """Initialize with the missing player ID."""
        self.player_id = player_id
        super().__init__(f"Player with id '{player_id}' not found")


class PlayerAlreadyExistsError(PlayerError):
    """Raised when trying to create a player that already exists."""

    def __init__(self, name: str):
        """Initialize with the existing player name."""
        self.name = name
        super().__init__(f"Player with name '{name}' already exists")


class InvalidPlayerIdError(PlayerError):
    """Raised when a player ID is not a valid UUID."""

    def __init__(self, player_id: str):
        """Initialize with the invalid player ID."""
        self.player_id = player_id
        super().__init__(f"Invalid player ID format: '{player_id}'")


class NameAlreadyTakenError(PlayerError):
    """Raised when trying to rename a player to an existing name."""

    def __init__(self, name: str):
        """Initialize with the taken name."""
        self.name = name
        super().__init__(f"Name '{name}' is already taken by another player")
