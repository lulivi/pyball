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

"""Tests for the SetLineup use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup import CreateTeams, SetLineup
from pyball.application.meetup.create_teams_algorithms import RandomAlgorithm
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import PlayerId

DATE = datetime(2026, 7, 15, 20, 0)


def _repo(meetup):
    repo = MagicMock()
    repo.find_by_datetime.return_value = meetup
    repo.find_all.return_value = [meetup]
    return repo


def test_trims_roster_and_builds_teams_in_one_save():
    """The roster becomes the lineup and two teams are built, saved once."""
    meetup = Meetup.create(DATE, "Campo")
    for _ in range(12):
        meetup.add_player(PlayerId.generate())
    lineup = meetup.players[:10]
    repo = _repo(meetup)

    result = SetLineup(repo, 10, CreateTeams(repo, RandomAlgorithm())).execute(DATE, lineup)

    assert result.players == lineup
    assert sum(len(t.players) for t in result.teams) == 10
    repo.save.assert_called_once_with(meetup)


def test_without_algorithm_leaves_no_teams():
    """Without an algorithm only the roster changes."""
    meetup = Meetup.create(DATE, "Campo")
    repo = _repo(meetup)
    result = SetLineup(repo, 10, None).execute(DATE, [PlayerId.generate()])
    assert result.teams is None


def test_failing_team_build_saves_nothing():
    """Too few players for teams leaves the stored meetup untouched."""
    meetup = Meetup.create(DATE, "Campo")
    repo = _repo(meetup)
    with pytest.raises(ValueError):
        SetLineup(repo, 10, CreateTeams(repo, RandomAlgorithm())).execute(
            DATE, [PlayerId.generate()]
        )
    repo.save.assert_not_called()
