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
"""Create teams manually use case."""

from datetime import datetime

from pyball.application.fuzzy_match import fuzzy_match_player
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


class CreateTeamsManually:
    """Use case for manually assigning players to teams by name."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
    ) -> None:
        """Initialize with repositories."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository

    def execute(
        self,
        meetup_date: datetime,
        team_a_names: list[str],
        team_b_names: list[str],
    ) -> Meetup:
        """Assign players to teams by name.

        Args:
            meetup_date: Exact datetime of the meetup.
            team_a_names: Player names for team A.
            team_b_names: Player names for team B.

        Returns:
            The updated meetup with teams set.

        Raises:
            MeetupNotFoundError: No meetup at meetup_date.
            ValueError: Name unresolvable, player not in meetup, overlap between
                        teams, uncovered meetup players, or unequal team sizes.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))

        all_players = self.player_repository.find_all()
        player_names_map = {p.id: p.name for p in all_players}

        unmatched: list[str] = []
        team_a_ids = []
        team_b_ids = []

        for name in team_a_names:
            try:
                team_a_ids.append(fuzzy_match_player(name, all_players).player_id)
            except ValueError:
                unmatched.append(name)

        for name in team_b_names:
            try:
                team_b_ids.append(fuzzy_match_player(name, all_players).player_id)
            except ValueError:
                unmatched.append(name)

        if unmatched:
            raise ValueError(f"Jugadores no encontrados: {', '.join(unmatched)}")

        not_in_meetup = [pid for pid in team_a_ids + team_b_ids if pid not in meetup.players]
        if not_in_meetup:
            names = [player_names_map.get(pid, str(pid)) for pid in not_in_meetup]
            raise ValueError(f"Jugadores no están en el meetup: {', '.join(names)}")

        overlap = set(team_a_ids) & set(team_b_ids)
        if overlap:
            names = [player_names_map.get(pid, str(pid)) for pid in overlap]
            raise ValueError(f"Jugadores asignados a los dos equipos: {', '.join(names)}")

        uncovered = [pid for pid in meetup.players if pid not in set(team_a_ids) | set(team_b_ids)]
        if uncovered:
            names = [player_names_map.get(pid, str(pid)) for pid in uncovered]
            raise ValueError(f"Jugadores sin equipo asignado: {', '.join(names)}")

        if len(team_a_ids) != len(team_b_ids):
            raise ValueError(
                f"Los equipos deben tener el mismo número de jugadores "
                f"({len(team_a_ids)} vs {len(team_b_ids)})"
            )

        meetup.set_teams([Team.create("A", team_a_ids), Team.create("B", team_b_ids)])
        self.meetup_repository.save(meetup)
        return meetup
