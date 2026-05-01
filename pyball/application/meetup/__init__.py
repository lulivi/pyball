# Copyright (c) 2026 Luis Liñán
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
"""Meetup use cases."""

from pyball.application.meetup.add_player import AddPlayerToMeetup
from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    ComputeStats,
    PlayerStats,
    StatsReport,
    StatsScopedReport,
)
from pyball.application.meetup.create_meetup import CreateMeetup, DuplicateMeetupError
from pyball.application.meetup.create_teams import CreateTeams
from pyball.application.meetup.finish_match import FinishMatch, MeetupAlreadyClosedError
from pyball.application.meetup.remove_player import RemovePlayerFromMeetup
from pyball.application.meetup.start_match import MeetupHasNoTeamsError, StartMatch

__all__ = [
    "CreateMeetup",
    "DuplicateMeetupError",
    "AddPlayerToMeetup",
    "RemovePlayerFromMeetup",
    "CreateTeams",
    "StartMatch",
    "MeetupHasNoTeamsError",
    "FinishMatch",
    "MeetupAlreadyClosedError",
    "ComputeStats",
    "StatsReport",
    "StatsScopedReport",
    "PlayerStats",
    "ChemistryPair",
]
