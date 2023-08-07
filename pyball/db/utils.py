# pylint: disable=no-value-for-parameter,not-an-iterable
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

"""Database utils."""

import datetime
import logging
import shutil

from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Tuple, Union

from peewee import IntegrityError, fn

from pyball.db import model, wrapper
from pyball.db.errors import (
    DbMatchesCountInconsistencyError,
    DbMatchStatisticsNotFoundError,
    DbMultiplePlayersFoundError,
    DbNoBackUpError,
    DbPlayerAlreadyExistentError,
    DbPlayerNotFoundError,
    DbPlayerNotUpdatedError,
    DbScoreInconsistencyError,
    DbStatisticForPlayerInMatchAlreadyExistent,
)
from pyball.logger import log_func

logger = logging.getLogger(__name__)


def get_results_names(score_0: int, score_1: int) -> Tuple[str, str]:
    """Get the stat that has to be increased for each team.

    :param score_0: Team 0 score.
    :param score_1: Team 1 score.
    :returns: The tuple of stat for team 0 and team 1.

    """
    if score_0 > score_1:
        return ("wins", "losses")
    if score_0 < score_1:
        return ("losses", "wins")
    return ("ties", "ties")


@log_func
def find_player(player: Union[str, int]) -> wrapper.Player:
    """Obtain a player by it's name or id.

    If the player was not found, search for a wild-card of the name.

    :param player: The id or the name of the player.
    :raises DbMultiplePlayersFoundError: When the name search retrieves multiple users.
    :raises DbPlayerNotFoundError: When the player or wild-card is not found in the database.
    :returns: The player.

    """
    player_is_str: bool = False
    try:
        operation = model.Player.telegram_id == int(player)
    except ValueError:
        operation = model.Player.name == player
        player_is_str = True

    player_list = model.Player.select().where(operation)

    if not player_list and player_is_str:
        player_list = model.Player.select().where(model.Player.name.contains(player))

        if len(player_list) > 1:
            raise DbMultiplePlayersFoundError(
                player_names=[p.name for p in player_list], wild_card=str(player)
            )
    try:
        return wrapper.Player.from_db(player_list.get())
    except model.Player.DoesNotExist as error:  # type: ignore  # pylint: disable=E1101
        raise DbPlayerNotFoundError(str(player)) from error


@log_func
def create_player(
    player_name: str, player_id: Optional[int] = None, main_player: bool = False
) -> None:
    """Add a new player to the database.

    :param player_name: Name of the new player.
    :param player_id: Id for the new player. If not set, automatic ID will be provided.
    :param main_player: Wether the player is part of the main team.
    :raises DbPlayerAlreadyExistentError: If the name or the id are already in the database.

    """
    table_info = {"name": player_name, "main": main_player}

    table_info["telegram_id"] = (
        player_id
        if player_id is not None
        else model.Player.select(fn.Max(model.Player.telegram_id)).scalar() + 1
    )

    try:
        model.Player.insert(**table_info).execute()
    except IntegrityError as error:
        raise DbPlayerAlreadyExistentError(player_name, player_id) from error


@log_func
def rename_player(player: Union[str, int], new_name: str) -> None:
    """Rename a player in the database.

    :param player: The id or the name of the player.
    :param new_name: The new name for the chosen player.
    :raises DbPlayerNotUpdatedError: If no player was modified.
    :raises DbPlayerAlreadyExistentError: If a player with the same name already exists.

    """
    player_wrapper = find_player(player)

    try:
        if (
            model.Player.update({"name": new_name})
            .where(model.Player.telegram_id == player_wrapper.telegram_id)
            .execute()
        ) != 1:
            raise DbPlayerNotUpdatedError()
    except IntegrityError as error:
        player_error_wrapped = find_player(new_name)
        raise DbPlayerAlreadyExistentError(new_name, player_error_wrapped.telegram_id) from error


@log_func
def reid_player(player: Union[str, int], new_identifier: int) -> None:
    """Change the ID of a player in the database.

    :param player: The id or the name of the player.
    :param new_identifier: The new ID for the chosen player.
    :raises DbPlayerNotUpdatedError: If no player was modified.
    :raises DbPlayerAlreadyExistentError: If a player with the same ID already exists.

    """
    player_wrapper = find_player(player)

    try:
        if (
            model.Player.update({"telegram_id": new_identifier})
            .where(model.Player.telegram_id == player_wrapper.telegram_id)
            .execute()
        ) != 1:
            raise DbPlayerNotUpdatedError()
        model.MatchStatistic.update({"player": new_identifier}).where(
            model.MatchStatistic.player == player_wrapper.telegram_id
        ).execute()
    except IntegrityError as error:
        player_error_wrapped = find_player(new_identifier)
        raise DbPlayerAlreadyExistentError(player_error_wrapped.name, new_identifier) from error


@log_func
def get_player_list() -> List[wrapper.Player]:
    """Get the list of existing players in the database.

    :returns: All the players.

    """
    return list(model.Player.select().order_by(model.Player.name).objects(wrapper.Player))


@log_func
def get_player_id_list() -> List[wrapper.Player]:
    """Get the list of existing players telegram ids in the database.

    :returns: All the players ids.

    """
    return [player.telegram_id for player in get_player_list()]


@log_func
def get_matches_date_list() -> List[datetime.datetime]:
    """Obtain a list of the past matches date.

    :returns: The list of dates.

    """
    return [
        match_date.date
        for match_date in model.MatchStatistic.select(model.MatchStatistic.date)
        .group_by(model.MatchStatistic.date)
        .order_by(model.MatchStatistic.date)
    ]


@log_func
def get_match(date: datetime.datetime) -> Dict[str, dict]:
    """Obtain a match dictionary containing the teams and the players and scores.

    :param date: The match to find.
    :returns: The dictionary of the match.

    """
    teams = list(
        model.MatchStatistic.select(model.MatchStatistic.team, fn.SUM(model.MatchStatistic.goals))
        .where(model.MatchStatistic.date == date)
        .group_by(model.MatchStatistic.team)
    )
    players = list(
        model.MatchStatistic.select(model.MatchStatistic.player, model.MatchStatistic.team).where(
            model.MatchStatistic.date == date
        )
    )

    if not players or not teams:
        raise DbMatchStatisticsNotFoundError(date)

    match_info = {
        k.team: {
            "goles": k.goals,
            "jugadores": [p.player.name for p in players if p.team == k.team],
        }
        for k in teams
    }

    return match_info


@log_func
def add_match_results(match_statistics: List[wrapper.MatchStatistic]) -> None:
    """Insert the new smatch statistics into the database and update the players.

    :param match_statistics: A list of match statistics.
    :raises DbPlayerNotUpdatedError: If a player is not updated with the match result.

    """
    backup_database()
    already_inserted_stats = []
    for stat in match_statistics:
        try:
            model.MatchStatistic.insert(stat.db_dict()).execute()
            already_inserted_stats.append(stat)
        except IntegrityError as error:
            # Ensure the already created records are deleted after the error
            for inserted_stat in already_inserted_stats:
                model.MatchStatistic.delete().where(
                    model.MatchStatistic.date == stat.date,
                    model.MatchStatistic.player == inserted_stat.player,
                ).execute()
            player = find_player(stat.player)
            raise DbStatisticForPlayerInMatchAlreadyExistent(stat.date, player.name) from error
        player_update = {
            model.Player.goals: model.Player.goals + stat.goals,
            model.Player.assists: model.Player.assists + stat.assists,
        }
        if stat.result:
            player_update[getattr(model.Player, stat.result)] = (
                getattr(model.Player, stat.result) + 1
            )
        if (
            model.Player.update(player_update)
            .where(model.Player.telegram_id == stat.player)
            .execute()
            != 1
        ):
            raise DbPlayerNotUpdatedError("Couldn't update the player goals or assists")

    update_players_skill()
    try:
        check_inconsistencies()
    except (DbScoreInconsistencyError, DbMatchesCountInconsistencyError):
        fix_inconsistencies()


@log_func
def backup_database() -> None:
    """Create a backup of the database."""
    database_file: Path = Path(model.database.database).resolve()
    backup_database_file: Path = database_file.with_name(f"{database_file.name}.bck")
    shutil.copy(str(database_file), str(backup_database_file))


@log_func
def rollback_database() -> None:
    """Restore the last backup of the database."""
    database_file: Path = Path(model.database.database).resolve()
    backup_database_file: Path = database_file.with_name(f"{database_file.name}.bck")

    if not backup_database_file.exists():
        logger.info("No database backup to restore")
        raise DbNoBackUpError()

    shutil.copy(str(backup_database_file), str(database_file))


@log_func
def update_players_skill() -> None:
    """Update the skill of all the players in the database.

    :raises DbPlayerNotUpdatedError: if no skill is updated.

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
            .where(model.Player.telegram_id == player.telegram_id)
            .execute()
        ) != 1:
            raise DbPlayerNotUpdatedError("Could not update the player skill")


@log_func
def check_inconsistencies() -> None:
    """Check inconsistencies in the database related to goals, assists, wins, losses and ties.

    :raises DbScoreInconsistencyError: When the sum of the score in all the matches is different to
        the one in the player statistics.
    :raises DbMatchesCountInconsistencyError: When the sum of wins, losses or ties is different
        than the one found in the match statistics table.

    """
    for player in model.Player.select():
        stats = (
            model.MatchStatistic.select(
                fn.SUM(model.MatchStatistic.goals), fn.SUM(model.MatchStatistic.assists)
            )
            .where(model.MatchStatistic.player == player)
            .group_by(model.MatchStatistic.player)
            .get_or_none()
        )

        if stats is None and (player.goals != 0 or player.assists != 0):
            raise DbScoreInconsistencyError(
                f"DB incosistency ({player.name}): there are no match statistics but player goals"
                f" ({player.goals}) or assists ({player.assists}) are not zero"
            )
        elif stats and (stats.goals != player.goals or stats.assists != player.assists):
            raise DbScoreInconsistencyError(
                f"DB incosistency ({player.name}): match statistics ({stats.goals},"
                f" {stats.assists}) are different from the player ones ({player.goals},"
                f" {player.assists})"
            )

        matches = (
            model.MatchStatistic.select().where(model.MatchStatistic.player == player).count()
        )
        player_stats = player.wins + player.losses + player.ties

        if matches != player_stats:
            raise DbMatchesCountInconsistencyError(
                f"DB incosistency ({player.name}): the number of match statistics ({matches}) is"
                f" different to the sum of won, lost and tied games ({player_stats})"
            )


@log_func
def fix_inconsistencies() -> None:
    """Fix inconsistencies related to the sum of win, lost and tied matches and scores."""

    def default_match_result_stat() -> Dict[str, int]:
        """Get the base statistic for all player."""
        return {"wins": 0, "losses": 0, "ties": 0}

    dates = [
        s.date
        for s in model.MatchStatistic.select(model.MatchStatistic.date).group_by(
            model.MatchStatistic.date
        )
    ]

    player_match_result_stats: DefaultDict[str, Dict[str, int]] = defaultdict(
        default_match_result_stat
    )
    for date in dates:
        orange_players = model.MatchStatistic.select(model.MatchStatistic.player).where(
            model.MatchStatistic.date == date, model.MatchStatistic.team == "Naranja"
        )
        green_players = model.MatchStatistic.select(model.MatchStatistic.player).where(
            model.MatchStatistic.date == date, model.MatchStatistic.team == "Verde"
        )
        goals_orange = (
            model.MatchStatistic.select(fn.SUM(model.MatchStatistic.goals))
            .where(model.MatchStatistic.date == date, model.MatchStatistic.team == "Naranja")
            .group_by(model.MatchStatistic.team)
            .scalar()
        )
        goals_green = (
            model.MatchStatistic.select(fn.SUM(model.MatchStatistic.goals))
            .where(model.MatchStatistic.date == date, model.MatchStatistic.team == "Verde")
            .group_by(model.MatchStatistic.team)
            .scalar()
        )
        orange_stat, green_stat = get_results_names(goals_orange, goals_green)

        for player in orange_players:
            player_match_result_stats[player.player.name][orange_stat] += 1
        for player in green_players:
            player_match_result_stats[player.player.name][green_stat] += 1

    for player in model.Player.select():
        if (
            model.Player.update(player_match_result_stats[player.name])
            .where(model.Player.telegram_id == player.telegram_id)
            .execute()
            != 1
        ):
            logger.warning(
                f"Player {player.name} ({player.telegram_id})'s stats where not updated"
            )

        stats = (
            model.MatchStatistic.select(
                fn.SUM(model.MatchStatistic.goals),
                fn.SUM(model.MatchStatistic.assists),
            )
            .where(model.MatchStatistic.player == player)
            .get_or_none()
        )

        if (
            model.Player.update({"goals": stats.goals or 0, "assists": stats.assists or 0})
            .where(model.Player.telegram_id == player.telegram_id)
            .execute()
            != 1
        ):
            logger.warning(
                f"Player {player.name} ({player.telegram_id})'s scores where not updated"
            )
