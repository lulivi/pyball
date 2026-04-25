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
