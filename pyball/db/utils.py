import datetime

from typing import Dict, List, Optional, Union

from peewee import IntegrityError, fn

from pyball.db import model, wrapper
from pyball.db.errors import (
    PlayerAlreadyExistentError,
    PlayerNotUpdatedError,
    StatisticForPlayerInMatchAlreadyExistent,
)

MatchResultType = List[Dict[str, Union[str, int, datetime.datetime]]]


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


def get_match_dict():
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
            .namedtuples()
        )
        matches[match.date] = {k.team: k.goals for k in teams}

    return matches


def add_match_result_from_dict_list(match_result: MatchResultType) -> None:
    """Insert the new smatch statistics into the database and update the players.

    :param match_result: A dictionary containing the match statistics per player.
    :raises PlayerNotUpdatedError: If a player is not updated with the match result.

    """
    for stat in match_result:
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
                }
            )
            .where(model.Player.id == stat["player"])
            .execute()
            != 1
        ):
            raise PlayerNotUpdatedError("Couldn't update the player goals or assists")

    update_players_skill()


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
