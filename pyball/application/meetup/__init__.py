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
from pyball.application.meetup.assign_teams_by_id import AssignTeamsById
from pyball.application.meetup.cancel_meetup import CancelMeetup
from pyball.application.meetup.close_meetup import CloseMeetup
from pyball.application.meetup.compute_stats import (
    ChemistryPair,
    ComputeStats,
    PlayerStats,
    StatsReport,
    StatsScopedReport,
)
from pyball.application.meetup.create_meetup import CreateMeetup
from pyball.application.meetup.create_teams import CreateTeams
from pyball.application.meetup.create_teams_manually import CreateTeamsManually
from pyball.application.meetup.destroy_teams import DestroyTeams
from pyball.application.meetup.edit_match_result import EditMatchResult
from pyball.application.meetup.finish_match import FinishMatch
from pyball.application.meetup.format_match_summary import FormatMatchSummary
from pyball.application.meetup.get_active_meetup import GetActiveMeetup
from pyball.application.meetup.lock_meetup import LockMeetup
from pyball.application.meetup.parse_callup import CallupParseOutcome, ParseCallup
from pyball.application.meetup.parse_callup_text import (
    MatchedPlayer,
    ParseCallupText,
    ParseResult,
    PlayerCandidate,
)
from pyball.application.meetup.remove_player import RemovePlayerFromMeetup
from pyball.application.meetup.set_meetup_players import SetMeetupPlayers
from pyball.application.meetup.start_next_round import StartNextRound
from pyball.application.meetup.update_meetup_date import UpdateMeetupDate
from pyball.application.meetup.update_meetup_location import UpdateMeetupLocation
from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupAlreadyClosedError,
    MeetupHasNoTeamsError,
    UnknownAlgorithmError,
)

__all__ = [
    "CallupParseOutcome",
    "CreateMeetup",
    "DuplicateMeetupError",
    "AddPlayerToMeetup",
    "RemovePlayerFromMeetup",
    "CreateTeams",
    "AssignTeamsById",
    "CancelMeetup",
    "CloseMeetup",
    "CreateTeamsManually",
    "DestroyTeams",
    "LockMeetup",
    "StartNextRound",
    "MeetupHasNoTeamsError",
    "EditMatchResult",
    "FinishMatch",
    "FormatMatchSummary",
    "GetActiveMeetup",
    "MeetupAlreadyClosedError",
    "UnknownAlgorithmError",
    "ComputeStats",
    "StatsReport",
    "StatsScopedReport",
    "PlayerStats",
    "ChemistryPair",
    "ParseCallup",
    "ParseCallupText",
    "ParseResult",
    "MatchedPlayer",
    "PlayerCandidate",
    "SetMeetupPlayers",
    "UpdateMeetupDate",
    "UpdateMeetupLocation",
]
