"""Tests for AssignTeamsById use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.assign_teams_by_id import AssignTeamsById
from pyball.domain.meetup.errors import MeetupNotFoundError
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player


def _player(name: str) -> Player:
    return Player.create(name=name, group="regular")


def _meetup(*players: Player) -> Meetup:
    m = Meetup.create(datetime(2026, 5, 6, 20, 0), "Campo")
    for p in players:
        m.add_player(p.id)
    return m


def _use_case(meetup):
    repo = MagicMock()
    repo.find_by_datetime.return_value = meetup
    return AssignTeamsById(repo), repo


class TestAssignTeamsById:
    """Tests for AssignTeamsById use case."""

    def test_happy_path_assigns_teams(self):
        """Valid equal-sized non-overlapping IDs covering all players creates teams."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, repo = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
        )

        assert result.teams is not None
        assert p1.id in result.teams[0].players
        assert p2.id in result.teams[1].players
        repo.save.assert_called_once_with(meetup)

    def test_raises_meetup_not_found(self):
        """MeetupNotFoundError raised when no meetup exists at the given datetime."""
        repo = MagicMock()
        repo.find_by_datetime.return_value = None

        with pytest.raises(MeetupNotFoundError):
            AssignTeamsById(repo).execute(datetime(2026, 5, 6, 20, 0), ["uuid-a"], ["uuid-b"])

    def test_raises_on_overlap(self):
        """ValueError when the same player ID appears in both teams."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup)
        pid = str(p1.id.value)

        with pytest.raises(ValueError, match="dos equipos"):
            uc.execute(datetime(2026, 5, 6, 20, 0), [pid], [pid])

    def test_raises_on_unequal_sizes(self):
        """ValueError mentioning both counts when team sizes differ."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup)

        with pytest.raises(ValueError, match=r"1 vs 2"):
            uc.execute(
                datetime(2026, 5, 6, 20, 0),
                [str(p1.id.value)],
                [str(p2.id.value), str(p3.id.value)],
            )

    def test_roster_updated_to_submitted_players(self):
        """Players not in submitted teams are removed; new players are added."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2)  # p3 NOT originally in meetup
        uc, repo = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p3.id.value)],  # p3 is outside original roster
        )

        assert p3.id in result.players
        assert p2.id not in result.players
        repo.save.assert_called_once()

    def test_meetup_players_match_team_union_after_save(self):
        """After execution meetup.players equals team_a + team_b in order."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
        )

        assert list(result.players) == [p1.id, p2.id]
