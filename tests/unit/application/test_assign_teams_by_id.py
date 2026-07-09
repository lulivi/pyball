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
        """ValueError mentioning the limit when team sizes differ by more than 1."""
        p1, p2, p3, p4 = _player("Juan"), _player("Pedro"), _player("Carlos"), _player("Luis")
        meetup = _meetup(p1, p2, p3, p4)
        uc, _ = _use_case(meetup)

        with pytest.raises(ValueError, match="máximo 1"):
            uc.execute(
                datetime(2026, 5, 6, 20, 0),
                [str(p1.id.value)],
                [str(p2.id.value), str(p3.id.value), str(p4.id.value)],
            )

    def test_accepts_one_player_size_difference(self):
        """Teams of 6 and 5 players (±1 difference) are accepted."""
        players = [_player(f"Player{i}") for i in range(11)]
        meetup = _meetup(*players)
        uc, repo = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p.id.value) for p in players[:6]],
            [str(p.id.value) for p in players[6:]],
        )

        assert result.teams is not None
        assert len(result.teams[0].players) == 6
        assert len(result.teams[1].players) == 5
        repo.save.assert_called_once_with(meetup)

    def test_rejects_two_player_size_difference(self):
        """ValueError when team sizes differ by 2 (7 vs 5)."""
        players = [_player(f"Player{i}") for i in range(12)]
        meetup = _meetup(*players)
        uc, _ = _use_case(meetup)

        with pytest.raises(ValueError, match="máximo 1"):
            uc.execute(
                datetime(2026, 5, 6, 20, 0),
                [str(p.id.value) for p in players[:7]],
                [str(p.id.value) for p in players[7:]],
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

    def test_creates_first_pending_match_after_assigning_teams(self):
        """execute() auto-starts the first match, so /match works without a separate step."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
        )

        assert result.current_match() is not None
        assert set(result.current_match().teams_playing) == set(result.teams)

    def test_does_not_duplicate_pending_match_on_re_edit(self):
        """Re-editing teams mid-tournament (matches already exist) does not touch matches."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup)

        first = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
        )
        assert len(first.matches) == 1

        second = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p3.id.value)],
        )
        assert len(second.matches) == 1
        assert second.matches[0] is first.matches[0]

    def test_happy_path_assigns_three_teams(self):
        """Valid equal-sized non-overlapping IDs covering all players creates 3 teams."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, repo = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
            [str(p3.id.value)],
        )

        assert result.teams is not None
        assert len(result.teams) == 3
        assert p1.id in result.teams[0].players
        assert p2.id in result.teams[1].players
        assert p3.id in result.teams[2].players
        repo.save.assert_called_once_with(meetup)

    def test_team_c_ids_none_keeps_two_team_result(self):
        """Omitting team_c_ids (None) still produces exactly 2 teams."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
            None,
        )

        assert result.teams is not None
        assert len(result.teams) == 2

    def test_raises_on_overlap_across_three_teams(self):
        """ValueError when the same player ID appears in team A and team C."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup)
        pid = str(p1.id.value)

        with pytest.raises(ValueError, match="más de un equipo"):
            uc.execute(
                datetime(2026, 5, 6, 20, 0),
                [pid],
                [str(p2.id.value)],
                [pid, str(p3.id.value)],
            )

    def test_raises_on_unequal_sizes_across_three_teams(self):
        """ValueError mentioning the limit when 3-team sizes differ by more than 1."""
        players = [_player(f"Player{i}") for i in range(6)]
        meetup = _meetup(*players)
        uc, _ = _use_case(meetup)

        with pytest.raises(ValueError, match="máximo 1"):
            uc.execute(
                datetime(2026, 5, 6, 20, 0),
                [str(players[0].id.value)],
                [str(players[1].id.value)],
                [str(p.id.value) for p in players[2:]],
            )

    def test_accepts_one_player_size_difference_across_three_teams(self):
        """Teams of 3, 3, 2 players (max-min = 1) are accepted."""
        players = [_player(f"Player{i}") for i in range(8)]
        meetup = _meetup(*players)
        uc, repo = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p.id.value) for p in players[:3]],
            [str(p.id.value) for p in players[3:6]],
            [str(p.id.value) for p in players[6:]],
        )

        assert result.teams is not None
        assert [len(t.players) for t in result.teams] == [3, 3, 2]
        repo.save.assert_called_once_with(meetup)

    def test_roster_updated_to_include_team_c_players(self):
        """meetup.players equals team_a + team_b + team_c in order when team_c is given."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2)  # p3 NOT originally in meetup
        uc, _ = _use_case(meetup)

        result = uc.execute(
            datetime(2026, 5, 6, 20, 0),
            [str(p1.id.value)],
            [str(p2.id.value)],
            [str(p3.id.value)],
        )

        assert list(result.players) == [p1.id, p2.id, p3.id]
