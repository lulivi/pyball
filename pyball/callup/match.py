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
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, List, Optional, Tuple, Union

from pyball import db
from pyball.callup.errors import (
    CallUpMatchTooManyTeamsForResults,
    CallUpMatchWrongPlayersNumberError,
    CallUpPlayersNotInMatch,
)
from pyball.callup.players import Players, find_player
from pyball.db.utils import add_match_results, get_results_names

logger = logging.getLogger(__name__)


class MatchStat:
    """Simple class for each stat."""

    def __init__(self, scorer: str, assistant: str = "") -> None:
        self.scorer = scorer.strip()
        self.assistant = assistant.strip()


class PlayersStatInput:
    """Player match stats."""

    def __init__(self) -> None:
        self._result: DefaultDict[str, Dict[str, int]] = defaultdict(self._default_stat)

    @staticmethod
    def _default_stat() -> Dict[str, int]:
        """Get the base statistic for all player."""
        return {"goals": 0, "assists": 0}

    def as_dict(self) -> DefaultDict[str, Dict[str, int]]:
        """Return the result dictionary.

        :returns: Player stats dictionary.

        """
        return self._result

    def add_goal(self, player: str) -> None:
        """Add a goal to the player match statistics.

        :param player: Player name.

        """
        self._result[self._player_correct_name(player)]["goals"] += 1

    def add_assist(self, player: str) -> None:
        """Add an assist to the player match statistics.

        :param player: Player name.

        """
        self._result[self._player_correct_name(player)]["assists"] += 1

    @staticmethod
    def _player_correct_name(player_name: str) -> str:
        """Find the player name in the database.

        :param player_name: The input player name.
        :returns: The full player name if found in the database.

        """
        return find_player(player_name).name

    def __len__(self) -> int:
        return len(self._result)


@dataclass
class Team:
    """A team of the match."""

    players: List[db.wrapper.Player] = field(default_factory=list)
    score: int = 0

    @property
    def skill(self) -> float:
        """Get the total skill of the team.

        :returns: The skill sum.

        """
        return sum(map(lambda p: p.skill, self.players))

    def append(self, value: db.wrapper.Player) -> None:
        """Add a new player to the team.

        :param value: The new player object.

        """
        self.players.append(value)

    def __len__(self) -> int:
        return len(self.players)

    def __getitem__(self, key: int) -> db.wrapper.Player:
        return self.players[key]

    def __setitem__(self, key: int, value: db.wrapper.Player):
        self.players[key] = value

    def __iter__(self):
        return iter(self.players)

    def __str__(self) -> str:
        player_join = "\n· ".join(map(lambda p: f"`{p.name}`", self.players))
        return f"· {player_join}"


class Match:
    """Necessary information involving a match.

    :cvar _team_names: Common team names to match for each team.
    :ivar _teams: Resulting teams.

    """

    __slots__ = ["_teams"]
    _team_names: Tuple[str, str, str] = ("Verde", "Naranja", "Sin Peto")

    def __init__(self) -> None:
        self._teams: List[Team] = []

    @property
    def teams(self) -> List[Team]:
        """Get the team list.

        :returns: The team list.

        """
        return self._teams

    @teams.setter
    def teams(self, teams: List[Team]) -> None:
        """Set the team list.

        :param teams: The team list.

        """
        if not teams or len(teams) < 2:
            raise ValueError("There should be at least to teams")

        self._teams = teams

    @staticmethod
    def auto_create(players: Players, teams_number: Optional[int] = None) -> "Match":
        """Create the teams automaticaly from a player list.

        :param players: The Players object.
        :param teams_number: The total number of teams.
        :returns: The new Match object.

        """
        match = Match()
        match._create_teams(players, teams_number)
        return match

    @staticmethod
    def manual_create(teams: List[Team]) -> "Match":
        """Create the Match manually.

        :param teams: The team list.
        :returns: The new Match object.

        """
        match = Match()
        match.teams = teams
        return match

    def _create_teams(self, players: Players, teams_number: Optional[int] = None) -> None:
        """Generate two balanced teams.

        :param players: The player list.
        :param teams_number: Number of team to create.

        """
        teams_number = teams_number or self._guess_teams_number(players)

        if 0 >= teams_number or teams_number > len(players) or len(players) % teams_number != 0:
            error = CallUpMatchWrongPlayersNumberError(len(players))
            logger.error(str(error))
            raise error

        logger.debug(f"Creating {teams_number} teams from the player list: {players!r}")
        self._teams = [Team() for _ in range(teams_number)]
        self._generate_teams(players, teams_number)
        self._balance_teams()

    @staticmethod
    def _guess_teams_number(players: Players) -> int:
        """Guess the number of teams that the match will have.

        :param players: List of players.
        :returns: The guessed number.

        """
        maximum = len(players)

        for teams_number in [2, 3]:
            if maximum % teams_number == 0 and len(players) / teams_number >= 5:
                return teams_number

        return 0

    def _generate_teams(self, players: Players, teams_number: int):
        """Divide the player list in teams.

        :param teams_number: Number of times to create.

        """
        self._teams = [Team() for _ in range(teams_number)]
        iterator = iter(sorted(players.players, key=lambda p: p.skill, reverse=True))
        zip_iters = [iterator] * teams_number

        for player_batch in zip(*zip_iters):
            self._teams.sort(key=lambda t: t.skill)

            for index, team in enumerate(self._teams):
                team.append(player_batch[index])

    def _balance_teams(self):
        """Perform a team balance.

        The algorithm consists in iteratin over the two lists at the same time and checking, after
        swapping the ``i`` item between the two lists, if the skill sum of each team is closser.

        """
        for index in range(len(self._teams[0])):
            team_1, team_2 = self._teams[0], self._teams[-1]

            diff1 = abs(team_1.skill - team_2.skill)
            team_1[index], team_2[index] = team_2[index], team_1[index]
            diff2 = abs(team_1.skill - team_2.skill)

            if diff2 < diff1:
                self._teams[0][index], self._teams[-1][index] = (
                    self._teams[-1][index],
                    self._teams[0][index],
                )

    def swap_players(self, first_player: Union[str, int], second_player: Union[str, int]) -> None:
        """Exange the two players between their teams.

        :param first_player: First player name or identifier.
        :param second_player: The other player name or identifier.

        """
        first_player_object: db.wrapper.Player = find_player(first_player)
        second_player_object: db.wrapper.Player = find_player(second_player)

        first_player_index_tuple = self._get_player_team(first_player_object)
        second_player_index_tuple = self._get_player_team(second_player_object)

        self._teams[first_player_index_tuple[0]].players.remove(first_player_object)
        self._teams[first_player_index_tuple[0]].players.insert(
            first_player_index_tuple[1], second_player_object
        )
        self._teams[second_player_index_tuple[0]].players.remove(second_player_object)
        self._teams[second_player_index_tuple[0]].players.insert(
            second_player_index_tuple[1], first_player_object
        )

    def _get_player_team(self, player: db.wrapper.Player) -> Tuple[int, int]:
        """Obtain the team in which the player will play.

        :param player: The player object to search for.
        :raises CallUpPlayersNotInMatch: If the player wasn't found in any of the teams.
        :returns: The team index.

        """
        for index, team in enumerate(self._teams):
            if player in team.players:
                return index, team.players.index(player)
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
        if len(self._teams) > 2:
            raise CallUpMatchTooManyTeamsForResults

        match_results_dict = match_results.as_dict()
        current_players = set(
            [
                player.name
                for player in itertools.chain(
                    *[team.players for team in self._teams],
                )
            ]
        )
        unplayed_players = set(match_results_dict) - (current_players)
        if unplayed_players:
            raise CallUpPlayersNotInMatch(list(unplayed_players))

        match_statistics: List[db.wrapper.MatchStatistic] = []
        for team_index, team in enumerate(self._teams):
            team.score = 0
            for player in team.players:
                goals_and_assists = match_results_dict.get(player.name, {"goals": 0, "assists": 0})
                team.score += goals_and_assists["goals"]
                match_statistics.append(
                    db.wrapper.MatchStatistic(
                        date=date,
                        team=self._team_names[team_index],
                        player=player.id,
                        goals=goals_and_assists["goals"],
                        assists=goals_and_assists["assists"],
                    )
                )

        team_0_names = [p.id for p in self._teams[0].players]
        team_0_result, team_1_result = get_results_names(*map(lambda x: x.score, self._teams))
        for stat in match_statistics:
            stat.set_result(team_0_result if stat.player in team_0_names else team_1_result)

        add_match_results(match_statistics)

    def __str__(self) -> str:
        if self._teams is None:
            return "No teams created yet."

        str_output = ""
        for team_name, team in zip(self._team_names[: len(self._teams)], self._teams):
            logger.debug(f"Team {team_name} ({team.skill}): {team}")
            str_output = f"{str_output}\nTeam {team_name}: {str(team.score)}\n{str(team)}\n"
        return str_output
