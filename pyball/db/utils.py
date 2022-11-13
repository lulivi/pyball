import datetime

from collections import defaultdict
from pprint import pprint
from typing import Dict, List, Optional, Tuple, Union

from peewee import IntegrityError, fn

from pyball.db import model, wrapper
from pyball.db.errors import (
    InconsistencyError,
    PlayerAlreadyExistentError,
    PlayerNotUpdatedError,
    ScoreInconsistencyError,
    MatchesCountInconsistencyError,
    StatisticForPlayerInMatchAlreadyExistent,
)

MatchResultType = List[Dict[str, Union[str, int, datetime.datetime]]]


def get_results_names(score_0: int, score_1: int) -> Tuple[str, str]:
    """Get the stat that has to be increased for each team.

    :param score_0: Team 0 score.
    :param score_1: Team 1 score.
    :returns: The tuple of stat for team 0 and team 1.

    """
    if score_0 > score_1:
        return "wins", "losses"
    if score_0 < score_1:
        return "losses", "wins"
    return "ties", "ties"


def find_player(player: Union[str, int]) -> wrapper.Player:
    """Obtain a player by it's name or id.

    :param player: The id or the name of the player
    :returns: The player.

    """
    try:
        operation = model.Player.id == int(player)
    except ValueError:
        operation = model.Player.name == player

    return wrapper.Player.from_db(model.Player.get(operation))


def create_player(
    player_name: str, player_id: Optional[int] = None, main_player: bool = False
) -> None:
    """Add a new player to the database.

    :param player_name: Name of the new player.
    :param player_id: Id for the new player. If not set, automatic ID will be provided.
    :param main_player: Wether the player is part of the main team.
    :raises PlayerAlreadyExistentError: If the name or the id are already in the database.

    """
    table_info = {"name": player_name, "main": main_player}

    if player_id is not None:
        table_info["id"] = player_id

    try:
        model.Player.insert(**table_info).execute()
    except IntegrityError as error:
        raise PlayerAlreadyExistentError(player_name, player_id) from error


def get_player_list() -> List[wrapper.Player]:
    """Get the list of existing players int he database.

    :returns: All the players.

    """
    return model.Player.select().objects(wrapper.Player)


def get_match_dict() -> Dict[datetime.datetime, Dict[str, int]]:
    """Get a list of the matches.

    :returns: The matches with their score.

    """
    matches = {}

    for match in (
        model.MatchStatistic.select(model.MatchStatistic.date)
        .group_by(model.MatchStatistic.date)
        .order_by(model.MatchStatistic.date)
    ):
        teams = list(
            model.MatchStatistic.select(
                model.MatchStatistic.team, fn.SUM(model.MatchStatistic.goals)
            )
            .where(model.MatchStatistic.date == match.date)
            .group_by(model.MatchStatistic.team)
        )
        matches[match.date] = {k.team: k.goals for k in teams}

    return matches


def format_match_list() -> str:
    """Get the list of matches.

    :returns: All the matches with their result.

    """
    match_list = ""

    for date, match in get_match_dict().items():
        match_list = (
            f"{match_list}{date.strftime('%Y/%m/%d %H:%M')}: Naranja {match['Naranja']} -"
            f" {match['Verde']} Verde\n"
        )
    return match_list


def add_match_result_from_dict_list(match_result: MatchResultType) -> None:
    """Insert the new smatch statistics into the database and update the players.

    :param match_result: A dictionary containing the match statistics per player.
    :raises PlayerNotUpdatedError: If a player is not updated with the match result.

    """
    for stat in match_result:
        wins, losses, ties = stat.pop("wins"), stat.pop("losses"), stat.pop("ties")
        try:
            model.MatchStatistic.insert(stat).execute()
        except IntegrityError:
            raise StatisticForPlayerInMatchAlreadyExistent(
                stat["date"], find_player(stat["player"])
            )
        if (
            model.Player.update(
                {
                    model.Player.goals: model.Player.goals + stat["goals"],
                    model.Player.assists: model.Player.assists + stat["assists"],
                    model.Player.wins: model.Player.wins + wins,
                    model.Player.losses: model.Player.losses + losses,
                    model.Player.ties: model.Player.ties + ties,
                }
            )
            .where(model.Player.id == stat["player"])
            .execute()
            != 1
        ):
            raise PlayerNotUpdatedError("Couldn't update the player goals or assists")

    update_players_skill()
    check_inconsistencies()


def update_players_skill() -> None:
    """Update the skill of all the players in the database.

    :raises PlayerNotUpdatedError: if no skill is updated.

    """
    goals = model.Player.select(
        fn.MIN(model.Player.goals).alias("min"), fn.MAX(model.Player.goals).alias("max")
    ).get()
    assists = model.Player.select(
        fn.MIN(model.Player.assists).alias("min"), fn.MAX(model.Player.assists).alias("max")
    ).get()

    for player in model.Player.select().objects(wrapper.Player):
        player.compute_skill(goals.min, goals.max, assists.min, assists.max)
        if (
            model.Player.update({model.Player.skill: player.skill})
            .where(model.Player.id == player.id)
            .execute()
        ) != 1:
            raise PlayerNotUpdatedError("Could not update the player skill")


def check_inconsistencies() -> None:
    """Check inconsistencies in the database related to goals, assists, wins, losses and ties.

    :raises ScoreInconsistencyError: When the sum of the score in all the matches is different to
        the one in the player statistics.
    :raises MatchesCountInconsistencyError: When the sum of wins, losses or ties is different than
        the one found in the match statistics table.

    """
    for p in model.Player.select():
        stats = (
            model.MatchStatistic.select(
                fn.SUM(model.MatchStatistic.goals), fn.SUM(model.MatchStatistic.assists)
            )
            .where(model.MatchStatistic.player == p)
            .group_by(model.MatchStatistic.player)
            .get_or_none()
        )

        if stats and (stats.goals != p.goals or stats.assists != p.assists):
            raise ScoreInconsistencyError(
                f"DB incosistency ({p.name}): match statistics ({stats.goals}, {stats.assists})"
                f" are different from the player ones ({p.goals}, {p.assists})"
            )

    for p in model.Player.select():
        matches = model.MatchStatistic.select().where(model.MatchStatistic.player == p).count()
        player_stats = p.wins + p.losses + p.ties
        if matches != player_stats:
            raise MatchesCountInconsistencyError(
                f"DB incosistency ({p.name}): the number of match statistics ({matches}) is"
                f" different to the sum of won, lost and tied games ({player_stats})"
            )


def fix_matches_count_incosistencies() -> None:
    """Fix inconsistencies related to the sum of win, lost and tied maches and scores."""

    def default_stat() -> Dict[str, int]:
        """Base statistic for all player."""
        return {"wins": 0, "losses": 0, "ties": 0}

    dates = [
        s.date
        for s in model.MatchStatistic.select(model.MatchStatistic.date).group_by(
            model.MatchStatistic.date
        )
    ]

    player_stats = defaultdict(default_stat)
    for d in dates:
        orange_players = model.MatchStatistic.select(model.MatchStatistic.player).where(
            model.MatchStatistic.date == d, model.MatchStatistic.team == "Naranja"
        )
        green_players = model.MatchStatistic.select(model.MatchStatistic.player).where(
            model.MatchStatistic.date == d, model.MatchStatistic.team == "Verde"
        )
        goals_orange = (
            model.MatchStatistic.select(fn.SUM(model.MatchStatistic.goals))
            .where(model.MatchStatistic.date == d, model.MatchStatistic.team == "Naranja")
            .group_by(model.MatchStatistic.team)
            .scalar()
        )
        goals_green = (
            model.MatchStatistic.select(fn.SUM(model.MatchStatistic.goals))
            .where(model.MatchStatistic.date == d, model.MatchStatistic.team == "Verde")
            .group_by(model.MatchStatistic.team)
            .scalar()
        )
        orange_stat, green_stat = get_results_names(goals_orange, goals_green)

        for p in orange_players:
            player_stats[p.player][orange_stat] += 1
        for p in green_players:
            player_stats[p.player][green_stat] += 1

    for p, stats in player_stats.items():
        if model.Player.update(stats).where(model.Player.id == p.id).execute() != 1:
            raise PlayerNotUpdatedError(
                f"There was an error updating player `{player.name} when fixing the match count"
            )

    for stat in (
        model.MatchStatistic.select(
            model.MatchStatistic.player,
            fn.SUM(model.MatchStatistic.goals),
            fn.SUM(model.MatchStatistic.assists),
        )
        .group_by(model.MatchStatistic.player)
        .dicts()
    ):
        player = stat.pop("player")
        if model.Player.update(stat).where(model.Player.id == player).execute() != 1:
            raise PlayerNotUpdatedError(
                f"There was an error updating player `{player.name} when fixing the scores"
            )
