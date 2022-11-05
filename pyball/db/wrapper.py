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

from dataclasses import dataclass

from pyball.db import model


@dataclass
class Player:
    """Player related information.

    :ivar id: Player unique identifier.
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

    id: int
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
        """Number of matches played by the player.

        :returns: The sum of won, lost and tied maches.

        """
        return self.wins + self.losses + self.ties

    def compute_skill(
        self, min_goals: int, max_goals: int, min_assists: int, max_assists: int
    ) -> None:
        win_perc = (
            ((self.wins + 0.5 * self.ties) / self.match_count) * 100 if self.match_count > 0 else 0
        )
        goals_perc = (self.goals - min_goals) / (max_goals - min_goals) * 100
        assists_perc = (self.assists - min_assists) / (max_assists - min_assists) * 100
        statistics = 0.6 * win_perc + 0.25 * goals_perc + 0.15 * assists_perc
        if self.rank:
            statistics = 0.7 * statistics + 0.3 * self.rank
        self.skill = statistics

    def as_dict(self) -> dict:
        return vars(self)

    def as_list(self) -> list:
        return [
            self.id,
            self.name,
            self.main,
            self.goals,
            self.assists,
            self.wins,
            self.losses,
            self.ties,
            self.rank,
            self.skill,
        ]

    @staticmethod
    def from_db(player: model.Player) -> "Player":
        return Player(
            id=player.id,
            name=player.name,
            main=player.main,
            goals=player.goals,
            assists=player.assists,
            wins=player.wins,
            losses=player.losses,
            ties=player.ties,
            rank=player.rank,
            skill=player.skill,
        )

    def __str__(self) -> str:
        return self.name
