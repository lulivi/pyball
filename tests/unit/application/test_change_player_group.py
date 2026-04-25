"""Tests for ChangePlayerGroup use case."""

from unittest.mock import MagicMock

from pyball.application.player.change_group import ChangePlayerGroup
from pyball.domain.player.models import Player


def test_change_player_group():
    """Changing a player's group updates and saves it."""
    player = Player.create(name="Mario", group="regular")
    repo = MagicMock()
    repo.find_by_id.return_value = player

    use_case = ChangePlayerGroup(repo)
    result = use_case.execute(str(player.id.value), "substitute")

    assert result.group == "substitute"
    repo.save.assert_called_once()
