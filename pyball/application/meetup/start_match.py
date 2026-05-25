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
"""Start match use case."""

import urllib.parse
from datetime import datetime

from pyball.domain.meetup.errors import MeetupHasNoTeamsError, MeetupNotFoundError
from pyball.domain.meetup.repository import MeetupRepository
from pyball.domain.player.repository import PlayerRepository


class StartMatch:
    """Use case for generating a match tracking URL."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
        base_url: str,
        team_colors: tuple[str, str] = ("blanco", "negro"),
        team_hex_bg: tuple[str, str] = ("#e4e4e7", "#27272a"),
        team_hex_text: tuple[str, str] = ("#27272a", "#e4e4e7"),
    ):
        """Initialize with repositories, base URL, and team color data."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository
        self.base_url = base_url
        self.team_colors = team_colors
        self.team_hex_bg = team_hex_bg
        self.team_hex_text = team_hex_text

    def execute(self, meetup_date: datetime) -> str:
        """Generate the match tracking URL for the given meetup date.

        Args:
            meetup_date: Meetup datetime.

        Returns:
            URL string with encoded team names, color params, and date.

        Raises:
            MeetupNotFoundError: If no meetup exists on that date.
            MeetupHasNoTeamsError: If the meetup has no teams yet.
        """
        meetup = self.meetup_repository.find_by_datetime(meetup_date)
        if meetup is None:
            raise MeetupNotFoundError(str(meetup_date))

        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")

        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        team_a_names = [player_names[str(pid.value)] for pid in meetup.teams[0].players]
        team_b_names = [player_names[str(pid.value)] for pid in meetup.teams[1].players]

        params = urllib.parse.urlencode(
            {
                "date": meetup_date.strftime("%Y-%m-%dT%H:%M"),
                "teamA": ",".join(team_a_names),
                "teamB": ",".join(team_b_names),
                "nameA": self.team_colors[0].capitalize(),
                "nameB": self.team_colors[1].capitalize(),
                "colorA": self.team_hex_bg[0],
                "colorB": self.team_hex_bg[1],
                "colorTextA": self.team_hex_text[0],
                "colorTextB": self.team_hex_text[1],
            }
        )
        return f"{self.base_url}/match?{params}"
