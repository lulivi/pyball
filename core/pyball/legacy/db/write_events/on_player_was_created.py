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

"""Create current and all seasons tables entries for the new player."""

from peewee import IntegrityError

from pyball.legacy.db import model
from pyball.legacy.db.errors import DbPlayerStatsAlreadyExistentError
from pyball.legacy.db.event_bus import PyBallEventBus
from pyball.legacy.db.events import Events
from pyball.logger import log_func


@PyBallEventBus.on(Events.ON_PLAYER_WAS_CREATED)
@log_func
def create_player_current_season_stats(player_id: int):
    """Create an entry of the recently created player in the current season stats table.

    :param player_id: The recently created player identifier.

    :raises DbPlayerStatsAlreadyExistentError: When the player stat is not inserted.

    """
    try:
        model.CurrentSeason.insert({"player": player_id}).execute()
    except IntegrityError as error:
        player = model.Player.select(model.Player.name).where(model.Player.id == player_id).get()
        raise DbPlayerStatsAlreadyExistentError(player.name, "CurrentSeason") from error


@PyBallEventBus.on(Events.ON_PLAYER_WAS_CREATED)
@log_func
def create_player_all_seasons_stats(player_id: int) -> None:
    """Create an entry of the recently created player in the all seasons stats table.

    :param player_id: The recently created player identifier.

    :raises DbPlayerStatsAlreadyExistentError: When the player stat is not inserted.

    """
    try:
        model.AllSeasons.insert({"player": player_id}).execute()
    except IntegrityError as error:
        player = model.Player.select(model.Player.name).where(model.Player.id == player_id).get()
        raise DbPlayerStatsAlreadyExistentError(player.name, "AllSeasons") from error
