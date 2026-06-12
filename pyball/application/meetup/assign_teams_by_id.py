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
"""Assign teams by player ID use case."""

from datetime import datetime

from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.models import PlayerId


class AssignTeamsById:
    """Use case for manually assigning players to teams by player ID."""

    def __init__(self, meetup_repository: MeetupRepository) -> None:
        """Initialize with the meetup repository."""
        self.meetup_repository = meetup_repository

    def execute(
        self,
        meetup_date: datetime,
        team_a_ids: list[str],
        team_b_ids: list[str],
    ) -> Meetup:
        """Assign players to teams by ID, updating the meetup roster accordingly.

        Args:
            meetup_date: Exact datetime of the meetup.
            team_a_ids: UUID strings for team A players.
            team_b_ids: UUID strings for team B players.

        Returns:
            The updated meetup with teams set.

        Raises:
            MeetupNotFoundError: No meetup at meetup_date.
            ValueError: Any player ID appears in both teams, or team sizes differ by more than 1.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))

        a_ids = [PlayerId.from_string(s) for s in team_a_ids]
        b_ids = [PlayerId.from_string(s) for s in team_b_ids]

        overlap = set(a_ids) & set(b_ids)
        if overlap:
            raise ValueError(
                f"Jugadores asignados a los dos equipos: "
                f"{', '.join(str(p.value) for p in overlap)}"
            )

        if abs(len(a_ids) - len(b_ids)) > 1:
            raise ValueError(
                f"Los equipos deben tener un tamaño similar, máximo 1 de diferencia "
                f"({len(a_ids)} vs {len(b_ids)})"
            )

        meetup.players[:] = a_ids + b_ids
        meetup.set_teams([Team.create("A", a_ids), Team.create("B", b_ids)])
        self.meetup_repository.save(meetup)
        return meetup
