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
        team_c_ids: list[str] | None = None,
    ) -> Meetup:
        """Assign players to teams by ID, updating the meetup roster accordingly.

        Args:
            meetup_date: Exact datetime of the meetup.
            team_a_ids: UUID strings for team A players.
            team_b_ids: UUID strings for team B players.
            team_c_ids: UUID strings for team C players, or None for a 2-team meetup.

        Returns:
            The updated meetup with teams set.

        Raises:
            MeetupNotFoundError: No meetup at meetup_date.
            ValueError: Any player ID appears in more than one team, or team sizes
                differ by more than 1 across all provided teams.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))

        groups = [
            [PlayerId.from_string(s) for s in team_a_ids],
            [PlayerId.from_string(s) for s in team_b_ids],
        ]
        if team_c_ids is not None:
            groups.append([PlayerId.from_string(s) for s in team_c_ids])

        all_ids = [pid for group in groups for pid in group]
        _raise_on_duplicates(all_ids, team_c_ids is not None)

        sizes = [len(group) for group in groups]
        if max(sizes) - min(sizes) > 1:
            raise ValueError(
                f"Los equipos deben tener un tamaño similar, máximo 1 de diferencia "
                f"({' vs '.join(str(s) for s in sizes)})"
            )

        meetup.players[:] = all_ids
        names = ["A", "B", "C"]
        meetup.set_teams([Team.create(names[i], group) for i, group in enumerate(groups)])
        self.meetup_repository.save(meetup)
        return meetup


def _raise_on_duplicates(all_ids: list[PlayerId], has_third_team: bool) -> None:
    """Raise ValueError listing any player ID that appears in more than one team."""
    seen: set[PlayerId] = set()
    dupes: set[PlayerId] = set()
    for pid in all_ids:
        if pid in seen:
            dupes.add(pid)
        seen.add(pid)
    if dupes:
        label = "más de un equipo" if has_third_team else "los dos equipos"
        raise ValueError(
            f"Jugadores asignados a {label}: {', '.join(str(p.value) for p in dupes)}"
        )
