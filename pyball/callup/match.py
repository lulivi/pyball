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

"""Match object."""
import datetime
import itertools

from typing import Dict, List, Optional, Tuple

from pyball.callup.errors import MatchWrongPlayersNumberError, StatisticOfNonPlayers
from pyball.callup.players import Players
from pyball.db import wrapper
from pyball.db.utils import MatchResultType, add_match_result_from_dict_list
from pyball.logger import PYBALL_LOGGER


class MatchResults:
    def __init__(self):
        self.__result: Dict[str, int] = {}

    def as_dict(self) -> MatchResultType:
        return self.__result

    def add_stat(self, player: str, goals: int = 0, assists: int = 0):
        self.__result[player] = {"goals": goals, "assists": assists}

    def __len__(self) -> int:
        return len(self.__result)


class Match:
    """Necessary information involving a match.

    :cvar __team_names: Common team names to mach for each team.
    :ivar __teams: Resulting teams.

    """

    __slots__ = ["__teams", "__score"]
    __team_names: Tuple[str] = ("Verde", "Naranja", "Sin peto")

    def __init__(self, players: Players, teams_number: Optional[int] = None) -> None:
        self.__teams: Optional[List[List[wrapper.Player]]] = None
        self.__create_teams(players, teams_number)
        self.__score: List[int] = [""] * len(self.__teams)

    def __create_teams(self, players: Players, teams_number: Optional[int] = None) -> None:
        """Generate two balanced teams.

        :param teams_number: Number of team to create.

        """

        teams_number = teams_number or self.__guess_teams_number(players)

        if 0 >= teams_number or teams_number > len(players) or len(players) % teams_number != 0:
            error = MatchWrongPlayersNumberError(len(players))
            PYBALL_LOGGER.error(str(error))
            raise error

        PYBALL_LOGGER.debug(f"Creating {teams_number} teams from the player list: {players}")
        self.__teams = [[] for _ in range(teams_number)]
        self.__generate_teams(players, teams_number)
        self.__balance_teams()

    def __guess_teams_number(self, players: Players) -> int:
        maximum = len(players)

        for teams_number in [2, 3]:
            if maximum % teams_number == 0 and len(players) / teams_number >= 5:
                return teams_number

        return 0

    def __generate_teams(self, players: Players, teams_number: int):
        """Divide the player list in teams.

        :param teams_number: Number of times to create.

        """
        iterator = iter(sorted(players.players, key=lambda p: p.skill, reverse=True))
        zip_iters = [iterator] * teams_number

        for player_batch in zip(*zip_iters):
            self.__teams.sort(key=lambda t: Match.__skill_sum(t))

            for i in range(len(self.__teams)):
                self.__teams[i].append(player_batch[i])

    @staticmethod
    def __skill_sum(players: List[wrapper.Player]) -> float:
        """Compute the total skill sum of the player list.

        :param players: List of players to compute the total sum.
        :returns: The sum.

        """
        return sum([p.skill for p in players])

    def __balance_teams(self):
        """Perform a team balance.

        The algorithm consists in iteratin over the two lists at the same time and checking, after
        swapping the ``i`` item between the two lists, if the skill sum of each team is closser.

        """
        for index in range(len(self.__teams[0])):
            team_1, team_2 = self.__teams[0][:], self.__teams[-1][:]

            diff1 = Match.__skill_diff(team_1, team_2)
            team_1[index], team_2[index] = team_2[index], team_1[index]
            diff2 = Match.__skill_diff(team_1, team_2)

            if diff2 < diff1:
                self.__teams[0][index], self.__teams[-1][index] = (
                    self.__teams[-1][index],
                    self.__teams[0][index],
                )

    @staticmethod
    def __skill_diff(team_a: List[wrapper.Player], team_b: List[wrapper.Player]) -> float:
        """Compute the difference between the two teams skill sum.

        :param team_a: First team to calculate the sum.
        :param team_b: Second team to calculate the sum.
        :returns: The difference.

        """
        return abs(Match.__skill_sum(team_a) - Match.__skill_sum(team_b))

    def set_results(self, match_results: MatchResults, date: datetime.datetime) -> None:
        match_results_dict = match_results.as_dict()
        current_players = set(map(lambda p: p.name, itertools.chain(*self.__teams)))
        unplayed_players = set(match_results_dict) - (current_players)
        if unplayed_players:
            raise StatisticOfNonPlayers(list(unplayed_players))

        db_results = []
        for team_index, team in enumerate(self.__teams):
            team_score = 0
            for player in team:
                goals_and_assists = match_results_dict.get(player.name, {"goals": 0, "assists": 0})
                team_score += goals_and_assists["goals"]
                db_results.append(
                    {
                        "date": date,
                        "team": self.__team_names[team_index],
                        "player": player.id,
                        **goals_and_assists,
                    }
                )
            self.__score[team_index] = team_score

        add_match_result_from_dict_list(db_results)

    def __str__(self) -> str:
        if self.__teams is None:
            return "No teams created yet."

        str_output = ""
        team_goals: str = ""
        for team_index, (team_name, team) in enumerate(
            zip(self.__team_names[: len(self.__teams)], self.__teams)
        ):
            team_list = "\n· ".join(map(lambda p: f"`{p.name}`", team))
            team_sum = Match.__skill_sum(team)
            PYBALL_LOGGER.debug(f"Team {team_name} ({team_sum}): {team}")
            if self.__score:
                team_goals = str(self.__score[team_index])
            str_output = f"{str_output}\nTeam {team_name}: {team_goals}\n· {team_list}\n"
        return str_output
