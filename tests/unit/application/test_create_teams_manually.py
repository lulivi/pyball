"""Tests for CreateTeamsManually use case."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from pyball.application.meetup.create_teams_manually import CreateTeamsManually
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


def _use_case(meetup, *players):
    meetup_repo = MagicMock()
    meetup_repo.find_by_datetime.return_value = meetup
    player_repo = MagicMock()
    player_repo.find_all.return_value = list(players)
    return CreateTeamsManually(meetup_repo, player_repo), meetup_repo


class TestCreateTeamsManually:
    """Tests for CreateTeamsManually use case."""

    def test_happy_path_creates_teams(self):
        """Valid names covering all meetup players with equal sizes creates teams."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, repo = _use_case(meetup, p1, p2)

        result = uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro"])

        assert result.teams is not None
        assert len(result.teams) == 2
        assert p1.id in result.teams[0].players
        assert p2.id in result.teams[1].players
        repo.save.assert_called_once_with(meetup)

    def test_creates_first_pending_match_after_assigning_teams(self):
        """execute() auto-starts the first match, so /match works without a separate step."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup, p1, p2)

        result = uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro"])

        assert result.current_match() is not None
        assert set(result.current_match().teams_playing) == set(result.teams)

    def test_raises_meetup_not_found(self):
        """MeetupNotFoundError raised when no meetup at given datetime."""
        meetup_repo = MagicMock()
        meetup_repo.find_by_datetime.return_value = None
        player_repo = MagicMock()

        with pytest.raises(MeetupNotFoundError):
            CreateTeamsManually(meetup_repo, player_repo).execute(
                datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro"]
            )

    def test_raises_when_name_unresolvable(self):
        """ValueError mentioning the bad name when fuzzy match fails."""
        p1 = _player("Juan")
        meetup = _meetup(p1)
        uc, _ = _use_case(meetup, p1)

        with pytest.raises(ValueError, match="Ghost"):
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Ghost"])

    def test_collects_all_unresolvable_names(self):
        """ValueError lists all bad names in a single exception, not just the first."""
        p1 = _player("Juan")
        meetup = _meetup(p1)
        uc, _ = _use_case(meetup, p1)

        with pytest.raises(ValueError) as exc_info:
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Ghost1"], ["Ghost2"])

        msg = str(exc_info.value)
        assert "Ghost1" in msg
        assert "Ghost2" in msg

    def test_raises_when_player_not_in_meetup(self):
        """ValueError listing players that resolved but aren't in the meetup."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1)  # p2 not in meetup

        meetup_repo = MagicMock()
        meetup_repo.find_by_datetime.return_value = meetup
        player_repo = MagicMock()
        player_repo.find_all.return_value = [p1, p2]

        with pytest.raises(ValueError, match="Pedro"):
            CreateTeamsManually(meetup_repo, player_repo).execute(
                datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro"]
            )

    def test_raises_when_player_in_both_teams(self):
        """ValueError listing players assigned to both teams."""
        p1, p2 = _player("Juan"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup, p1, p2)

        with pytest.raises(ValueError, match="Juan"):
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Juan"])

    def test_raises_when_meetup_player_uncovered(self):
        """ValueError listing meetup players not in either team."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup, p1, p2, p3)

        with pytest.raises(ValueError, match="Carlos"):
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro"])

    def test_raises_when_unequal_team_sizes(self):
        """ValueError with both counts when team sizes differ."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup, p1, p2, p3)

        with pytest.raises(ValueError, match=r"1 vs 2"):
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], ["Pedro", "Carlos"])

    def test_fuzzy_name_resolution(self):
        """A name with a minor typo is resolved via fuzzy matching."""
        p1, p2 = _player("Manuel"), _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup, p1, p2)

        result = uc.execute(datetime(2026, 5, 6, 20, 0), ["Manul"], ["Pedro"])  # typo

        assert result.teams is not None
        assert p1.id in result.teams[0].players

    def test_empty_team_b_auto_fills_from_remaining_players(self):
        """Empty team_b_names fills team B with meetup players not in team A."""
        p1, p2, p3, p4 = _player("Juan"), _player("Pedro"), _player("Carlos"), _player("Maria")
        meetup = _meetup(p1, p2, p3, p4)
        uc, repo = _use_case(meetup, p1, p2, p3, p4)

        result = uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan", "Pedro"], [])

        assert result.teams is not None
        team_a_ids = result.teams[0].players
        team_b_ids = result.teams[1].players
        assert p1.id in team_a_ids
        assert p2.id in team_a_ids
        assert p3.id in team_b_ids
        assert p4.id in team_b_ids
        repo.save.assert_called_once_with(meetup)

    def test_auto_fill_raises_on_unequal_team_sizes(self):
        """Auto-filled team B raises ValueError when resulting sizes differ."""
        p1, p2, p3 = _player("Juan"), _player("Pedro"), _player("Carlos")
        meetup = _meetup(p1, p2, p3)
        uc, _ = _use_case(meetup, p1, p2, p3)

        with pytest.raises(ValueError, match=r"1 vs 2"):
            uc.execute(datetime(2026, 5, 6, 20, 0), ["Juan"], [])

    def test_names_with_parentheses_resolve(self):
        """Player names containing parentheses are resolved correctly."""
        p1 = _player("Manuel (Antonio)")
        p2 = _player("Pedro")
        meetup = _meetup(p1, p2)
        uc, _ = _use_case(meetup, p1, p2)

        result = uc.execute(datetime(2026, 5, 6, 20, 0), ["Manuel (Antonio)"], ["Pedro"])

        assert result.teams is not None
        assert p1.id in result.teams[0].players
