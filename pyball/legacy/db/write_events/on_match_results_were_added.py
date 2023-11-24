# Copyright (c) 2023 Luis Liñán
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

"""Execute functions once the match results are added to the database."""

import datetime
import logging

from typing import Dict, Type, Union

from peewee import fn

from pyball.db import model, wrapper
from pyball.db.errors import DbPlayerNotUpdatedError
from pyball.db.event_bus import PyBallEventBus
from pyball.db.events import Events
from pyball.db.utils import get_last_end_of_august
from pyball.logger import log_func

logger = logging.getLogger(__name__)


@PyBallEventBus.on(Events.ON_MATCH_RESULTS_WHERE_ADDED)
@log_func
def update_current_season_player_table(date: datetime.datetime, results: Dict[int, str]) -> None:
    """Update the skill of all players in the database for the current season.

    :param date: The match date which will be used to update the stats.
    :param results: The outcome of the match for each player.
    :raises DbPlayerNotUpdatedError: if no skill is updated.

    """
    if date < get_last_end_of_august():
        logger.debug(
            "The added match date is before this season start, so no current seasons statistics"
            " will be modified"
        )
        return

    _update_player_season_stats(
        date=date,
        results=results,
        season_stats_table=model.CurrentSeason,
    )


@PyBallEventBus.on(Events.ON_MATCH_RESULTS_WHERE_ADDED)
@log_func
def update_all_seasons_player_table(date: datetime.datetime, results: Dict[int, str]) -> None:
    """Update the skill of all players in the database for the all the seasons.

    :param date: The match date which will be used to update the stats.
    :param results: The outcome of the match for each player.
    :raises DbPlayerNotUpdatedError: if no skill is updated.

    """
    _update_player_season_stats(
        date=date,
        results=results,
        season_stats_table=model.AllSeasons,
    )


def _update_player_season_stats(
    date: datetime.datetime,
    results: Dict[int, str],
    season_stats_table: Union[Type[model.CurrentSeason], Type[model.AllSeasons]],
) -> None:
    """Update the players skill and statas for a given date and table.

    :param date: The match date which will be used to update the stats.
    :param results: The outcome of the match for each player.
    :param season_stats_table: The database table of the stats to update.

    """
    for statistic in model.MatchStatistic.select().where(model.MatchStatistic.date == date):
        current_season_stat = getattr(season_stats_table, results[statistic.player.id])

        season_stats_update = season_stats_table.update(
            {
                season_stats_table.goals: season_stats_table.goals + statistic.goals,
                season_stats_table.assists: season_stats_table.assists + statistic.assists,
                current_season_stat: current_season_stat + 1,
            }
        ).where(season_stats_table.player == statistic.player)
        if season_stats_update.execute() != 1:
            raise DbPlayerNotUpdatedError("Could not update player stats")

    goals_and_assists = season_stats_table.select(
        fn.MIN(season_stats_table.goals).alias("goals_minimum"),
        fn.MAX(season_stats_table.goals).alias("goals_maximum"),
        fn.MIN(season_stats_table.assists).alias("assists_minimum"),
        fn.MAX(season_stats_table.assists).alias("assists_maximum"),
    ).get()

    player: wrapper.Player
    for player in (
        model.Player.select(
            model.Player.id,
            model.Player.telegram_id,
            model.Player.name,
            model.Player.main,
            model.Player.rank,
            season_stats_table.goals,
            season_stats_table.assists,
            season_stats_table.wins,
            season_stats_table.losses,
            season_stats_table.ties,
            season_stats_table.skill,
        )
        .join(season_stats_table)
        .objects(wrapper.Player)
    ):
        player.compute_skill(
            goals_and_assists.goals_minimum,
            goals_and_assists.goals_maximum,
            goals_and_assists.assists_minimum,
            goals_and_assists.assists_maximum,
        )
        season_skill_update = season_stats_table.update(
            {season_stats_table.skill: player.skill}
        ).where(season_stats_table.player == player.id)
        if season_skill_update.execute() != 1:
            raise DbPlayerNotUpdatedError("Could not update the player skill")
