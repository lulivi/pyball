# Copyright (c) 2022 Luis Liñán
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

"""Classes wrappers for the database."""

import datetime

from dataclasses import dataclass
from typing import Optional, cast

from pyball.db import model
from pyball.db.errors import DbUnknownResultError


@dataclass
class Player:  # pylint: disable=too-many-instance-attributes
    """Player related information.

    :ivar _id: The database identifier of the player.
    :ivar telegram_id: Player unique telegram identifier.
    :ivar name: Common name.
    :ivar main: Whether if the player is main player in the club.
    :ivar goals: Number of goals.
    :ivar assists: Number of assists.
    :ivar wins: Number of won matches.
    :ivar losses: Number of lost matches.
    :ivar ties: Number of tied matches.
    :ivar rank: Skill rank of the player.
    :ivar skill: Skill level.

    """

    _id: int
    telegram_id: int
    name: str
    main: bool
    goals: int = 0
    assists: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    rank: int = 0
    skill: float = 0.0

    @property
    def match_count(self) -> int:
        """Retrieve the number of matches played by the player.

        :returns: The sum of won, lost and tied matches.

        """
        return self.wins + self.losses + self.ties

    def compute_skill(
        self, min_goals: int, max_goals: int, min_assists: int, max_assists: int
    ) -> None:
        """Calc the skill level for the player.

        :param min_goals: The least number of goals that a player has.
        :param max_goals: The maximum number of goals that a player has.
        :param min_assists: The least number of assists that a player has.
        :param max_assists: The maximum number of assists that a player has.

        """
        win_perc = (
            ((self.wins + 0.5 * self.ties) / self.match_count) * 100 if self.match_count > 0 else 0
        )
        goals_perc = (
            (self.goals - min_goals) / (max_goals - min_goals) * 100
            if (max_goals - min_goals)
            else 0
        )
        assists_perc = (
            (self.assists - min_assists) / (max_assists - min_assists) * 100
            if (max_assists - min_assists)
            else 0
        )
        statistics = 0.6 * win_perc + 0.25 * goals_perc + 0.15 * assists_perc

        if self.rank:
            statistics = 0.7 * statistics + 0.3 * self.rank

        self.skill = round(statistics, 5)

    @staticmethod
    def from_db(player: model.Player) -> "Player":
        """Create a Player object from the database Player class.

        :param player: The database Player object.
        :returns: The new Player instance.

        """
        return Player(
            _id=cast(int, player._id),  # pylint: disable=protected-access
            telegram_id=cast(int, player.telegram_id),
            name=cast(str, player.name),
            main=cast(bool, player.main),
            goals=cast(int, player.goals),
            assists=cast(int, player.assists),
            wins=cast(int, player.wins),
            losses=cast(int, player.losses),
            ties=cast(int, player.ties),
            rank=cast(int, player.rank),
            skill=cast(float, player.skill),
        )

    def __str__(self) -> str:
        return self.name


@dataclass
class MatchStatistic:
    """Match statistic information.

    :ivar date: Date of the match.
    :ivar player: Player object.
    :ivar team: Team name.
    :ivar goals: Number of goals.
    :ivar assists: Number of assists.

    """

    date: datetime.datetime
    player: int
    team: str
    goals: int
    assists: int
    result: Optional[str] = None

    def db_dict(self) -> dict:
        """Return the database necessary information.

        :returns: The dictionary containing the database columns.

        """
        return {
            "date": self.date,
            "player": self.player,
            "team": self.team,
            "goals": self.goals,
            "assists": self.assists,
        }

    def set_result(self, result: str) -> None:
        """Set the player result to update the player wins, losses or ties.

        :param result: A representation of the result.

        """
        if result not in ("wins", "losses", "ties"):
            raise DbUnknownResultError(result)
        self.result = result
