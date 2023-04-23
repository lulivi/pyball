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
import logging

from collections import defaultdict
from typing import DefaultDict, Dict, List, NamedTuple, Optional, Tuple, Union

from pyball import db
from pyball.callup.errors import (
    CallUpMatchWrongPlayersNumberError,
    CallUpMultiplePlayersFoundError,
    CallUpPlayerDoesNotExistError,
    CallUpPlayersNotInMatch,
)
from pyball.callup.players import Players
from pyball.db.utils import add_match_results, find_player, get_results_names

logger = logging.getLogger(__name__)


class MatchStat:
    """Simple class for each stat."""

    def __init__(self, scorer: str, assistant: str = "") -> None:
        self.scorer = scorer.strip()
        self.assistant = assistant.strip()


class PlayersStatInput:
    """Player match stats."""

    def __init__(self) -> None:
        self.__result: DefaultDict[str, Dict[str, int]] = defaultdict(self.__default_stat)

    @staticmethod
    def __default_stat() -> Dict[str, int]:
        """Get the base statistic for all player."""
        return {"goals": 0, "assists": 0}

    def as_dict(self) -> DefaultDict[str, Dict[str, int]]:
        """Return the result dictionary.

        :returns: Player stats dictionary.

        """
        return self.__result

    def add_goal(self, player: str) -> None:
        """Add a goal to the player match statistics.

        :param player: Player name.

        """
        self.__result[self.__player_correct_name(player)]["goals"] += 1

    def add_assist(self, player: str) -> None:
        """Add an assist to the player match statistics.

        :param player: Player name.

        """
        self.__result[self.__player_correct_name(player)]["assists"] += 1

    @staticmethod
    def __player_correct_name(player_name: str) -> str:
        """Find the player name in the database.

        :param player_name: The input player name.
        :returns: The full player name if found in the database.

        """
        try:
            real_player_name: db.wrapper.Player = find_player(player_name)
        except db.model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
            raise CallUpPlayerDoesNotExistError(player_name) from error
        except db.errors.DbMultiplePlayersFoundError as error:
            raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error

        return real_player_name.name

    def __len__(self) -> int:
        return len(self.__result)


class Match:
    """Necessary information involving a match.

    :cvar __team_names: Common team names to match for each team.
    :ivar __teams: Resulting teams.

    """

    __slots__ = ["__teams", "__score"]
    __team_names: Tuple[str, str, str] = ("Verde", "Naranja", "Sin peto")

    def __init__(self, players: Players, teams_number: Optional[int] = None) -> None:
        self.__teams: List[List[db.wrapper.Player]]
        self.__create_teams(players, teams_number)
        self.__score: List[int] = [0] * len(self.__teams)

    def __create_teams(self, players: Players, teams_number: Optional[int] = None) -> None:
        """Generate two balanced teams.

        :param teams_number: Number of team to create.

        """
        teams_number = teams_number or self.__guess_teams_number(players)

        if 0 >= teams_number or teams_number > len(players) or len(players) % teams_number != 0:
            error = CallUpMatchWrongPlayersNumberError(len(players))
            logger.error(str(error))
            raise error

        logger.debug(f"Creating {teams_number} teams from the player list: {players}")
        self.__teams = [[] for _ in range(teams_number)]
        self.__generate_teams(players, teams_number)
        self.__balance_teams()

    @staticmethod
    def __guess_teams_number(players: Players) -> int:
        """Guess the number of teams that the match will have.

        :param players: List of players.
        :returns: The guessed number.

        """
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
            self.__teams.sort(key=Match.__skill_sum)

            for index, team in enumerate(self.__teams):
                team.append(player_batch[index])

    @staticmethod
    def __skill_sum(players: List[db.wrapper.Player]) -> float:
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
    def __skill_diff(team_a: List[db.wrapper.Player], team_b: List[db.wrapper.Player]) -> float:
        """Compute the difference between the two teams skill sum.

        :param team_a: First team to calculate the sum.
        :param team_b: Second team to calculate the sum.
        :returns: The difference.

        """
        return abs(Match.__skill_sum(team_a) - Match.__skill_sum(team_b))

    def swap_players(self, first_player: Union[str, int], second_player: Union[str, int]) -> None:
        """Exange the two players between their teams.

        :param first_player: First player name or identifier.
        :param second_player: The other player name or identifier.

        """
        try:
            first_player_object: db.wrapper.Player = find_player(first_player)
        except db.model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
            raise CallUpPlayerDoesNotExistError(first_player) from error
        except db.errors.DbMultiplePlayersFoundError as error:
            raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error
        try:
            second_player_object: db.wrapper.Player = find_player(second_player)
        except db.model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
            raise CallUpPlayerDoesNotExistError(second_player) from error
        except db.errors.DbMultiplePlayersFoundError as error:
            raise CallUpMultiplePlayersFoundError(error.players, error.wild_card) from error

        first_player_index_tuple = self.__get_player_team(first_player_object)
        second_player_index_tuple = self.__get_player_team(second_player_object)

        self.__teams[first_player_index_tuple[0]].remove(first_player_object)
        self.__teams[first_player_index_tuple[0]].insert(
            first_player_index_tuple[1], second_player_object
        )
        self.__teams[second_player_index_tuple[0]].remove(second_player_object)
        self.__teams[second_player_index_tuple[0]].insert(
            second_player_index_tuple[1], first_player_object
        )

    def __get_player_team(self, player: db.wrapper.Player) -> Tuple[int, int]:
        """Obtain the team in which the player will play.

        :param player: The player object to search for.
        :raises CallUpPlayersNotInMatch: If the player wasn't found in any of the teams.
        :returns: The team index.

        """
        for index, team in enumerate(self.__teams):
            if player in team:
                return index, team.index(player)
        raise CallUpPlayersNotInMatch([player.name])

    def set_results(self, match_results: PlayersStatInput, date: datetime.datetime) -> None:
        """Calculate and pass the necessary information to the database.

        This function will prepare a list of dictionaries containing the date, player id, team,
        goals, assists necessary to insert the data into the MatchStatistic table. Also the wins,
        losses and ties to the Player table.

        :param match_results: A dictionary of players with their corresponding goals and assists in
            the match.
        :param date: Date of the match.

        """
        match_results_dict = match_results.as_dict()
        current_players = set(map(lambda p: p.name, itertools.chain(*self.__teams)))
        unplayed_players = set(match_results_dict) - (current_players)
        if unplayed_players:
            raise CallUpPlayersNotInMatch(list(unplayed_players))

        match_statistics: List[db.wrapper.MatchStatistic] = []
        for team_index, team in enumerate(self.__teams):
            self.__score[team_index] = 0
            for player in team:
                goals_and_assists = match_results_dict.get(player.name, {"goals": 0, "assists": 0})
                self.__score[team_index] += goals_and_assists["goals"]
                match_statistics.append(
                    db.wrapper.MatchStatistic(
                        date=date,
                        team=self.__team_names[team_index],
                        player=player.id,
                        goals=goals_and_assists["goals"],
                        assists=goals_and_assists["assists"],
                    )
                )

        if len(self.__teams) == 2:
            team_0_names = [p.id for p in self.__teams[0]]
            team_0_result, team_1_result = get_results_names(*self.__score)
            for stat in match_statistics:
                stat.set_result(team_0_result if stat.player in team_0_names else team_1_result)

        add_match_results(match_statistics)

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
            logger.debug(f"Team {team_name} ({team_sum}): {team}")
            if self.__score:
                team_goals = str(self.__score[team_index])
            str_output = f"{str_output}\nTeam {team_name}: {team_goals}\n· {team_list}\n"
        return str_output
