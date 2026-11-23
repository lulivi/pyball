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

"""Tests for the CreateTeams use case."""

import logging
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.create_teams import CreateTeams
from pyball.application.meetup.create_teams_algorithms.algorithm import TeamAssignment
from pyball.domain.meetup.errors import MeetupHasRecordedResultsError, MeetupNotFoundError
from pyball.domain.meetup.models import Match, MatchResult, Meetup, PlayerId, Team


class StubAlgorithm:
    """Stub that splits players in half deterministically."""

    def assign(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, players, _finished_meetups, _season_meetups, _season_start, _team_count=2
    ):
        """Split players in half and return two groups."""
        mid = len(players) // 2
        return (TeamAssignment(players=players[:mid]), TeamAssignment(players=players[mid:]))


class TestCreateTeams:
    """Tests for CreateTeams use case."""

    def test_raises_when_meetup_not_found(self):
        """MeetupNotFoundError is raised when the meetup does not exist."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None
        use_case = CreateTeams(repo, StubAlgorithm())

        with pytest.raises(MeetupNotFoundError):
            use_case.execute(datetime(2026, 5, 6, 20, 0))

    def test_delegates_assignment_to_algorithm(self):
        """execute() calls algorithm.assign() and applies the returned teams."""
        players = [PlayerId.generate() for _ in range(4)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        repo.find_all.return_value = []

        algorithm = MagicMock()
        algorithm.assign.return_value = (
            TeamAssignment(players=players[:2]),
            TeamAssignment(players=players[2:]),
        )

        use_case = CreateTeams(repo, algorithm)
        result = use_case.execute(datetime(2026, 5, 6, 20, 0))

        algorithm.assign.assert_called_once()
        repo.save.assert_called_once_with(meetup)
        assert result.teams is not None
        assert len(result.teams) == 2

    def test_passes_season_start_datetime_to_algorithm(self):
        """execute() passes a datetime object as season_start to algorithm.assign()."""
        players = [PlayerId.generate() for _ in range(2)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        repo.find_all.return_value = []

        algorithm = MagicMock()
        algorithm.assign.return_value = (
            TeamAssignment(players=players[:1]),
            TeamAssignment(players=players[1:]),
        )

        CreateTeams(repo, algorithm).execute(datetime(2026, 5, 6, 20, 0))

        _, _, _, season_start, _ = algorithm.assign.call_args.args
        assert isinstance(season_start, datetime)

    def test_saves_meetup_after_assigning_teams(self):
        """Meetup is persisted after teams are set."""
        players = [PlayerId.generate() for _ in range(4)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        repo.find_all.return_value = []

        use_case = CreateTeams(repo, StubAlgorithm())
        use_case.execute(datetime(2026, 5, 6, 20, 0))

        repo.save.assert_called_once()

    def test_creates_first_pending_match_after_assigning_teams(self):
        """execute() auto-starts the first match, so /match works without a separate step."""
        players = [PlayerId.generate() for _ in range(4)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        repo.find_all.return_value = []

        result = CreateTeams(repo, StubAlgorithm()).execute(datetime(2026, 5, 6, 20, 0))

        assert result.current_match() is not None
        assert set(result.current_match().teams_playing) == set(result.teams)

    def test_execute_logs_team_generation_at_info(self, caplog):
        """Generating teams emits one INFO record on its logger."""
        players = [PlayerId.generate() for _ in range(4)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        repo.find_all.return_value = []

        with caplog.at_level(logging.INFO, logger="pyball.application.meetup.create_teams"):
            CreateTeams(repo, StubAlgorithm()).execute(datetime(2026, 5, 6, 20, 0))

        recs = [r for r in caplog.records if r.name == "pyball.application.meetup.create_teams"]
        assert len(recs) == 1
        assert recs[0].levelno == logging.INFO
        assert "teams generated" in recs[0].getMessage().lower()

    def test_raises_when_meetup_has_recorded_results(self):
        """MeetupHasRecordedResultsError is raised once a result exists, teams untouched."""
        players = [PlayerId.generate() for _ in range(4)]
        meetup = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
        for p in players:
            meetup.add_player(p)
        meetup.set_teams([Team.create("A", players[:2]), Team.create("B", players[2:])])
        meetup.add_match(
            Match(
                teams_playing=(meetup.teams[0], meetup.teams[1]),
                result=MatchResult(score_a=1, score_b=0, events=()),
            )
        )
        original_teams = meetup.teams

        repo = MagicMock()
        repo.find_by_datetime.return_value = meetup
        use_case = CreateTeams(repo, StubAlgorithm())

        with pytest.raises(MeetupHasRecordedResultsError):
            use_case.execute(datetime(2026, 5, 6, 20, 0))

        assert meetup.teams == original_teams
        repo.save.assert_not_called()
