"""Unit tests for Container."""

from unittest.mock import MagicMock, patch

import pytest

from pyball.application.container import Container
from pyball.application.meetup import AddPlayerToMeetupById, RemovePlayerFromMeetupById
from pyball.infrastructure.http.links import SignupLinkBuilder


class TestContainerInit:
    """Tests for Container.__init__."""

    def test_stores_injected_settings(self):
        """Container exposes injected settings through use cases."""
        settings = MagicMock()
        settings.pyball.location = "Test Field"
        container = Container(settings)
        use_case = container.create_meetup()
        assert use_case is not None

    def test_legacy_stats_path_uses_settings_data_dir(self, tmp_path):
        """legacy_stats uses settings.paths.data_dir to locate the file."""
        settings = MagicMock()
        settings.paths.data_dir = tmp_path
        container = Container(settings)
        with patch("pyball.application.container.LegacyStats.from_file") as mock_from_file:
            mock_from_file.return_value = MagicMock()
            _ = container.legacy_stats
        mock_from_file.assert_called_once_with(str(tmp_path / "legacy_stats.json"))

    def test_requires_settings_argument(self):
        """Container requires a settings argument."""
        with pytest.raises(TypeError):
            Container()  # type: ignore[call-arg]  # pylint: disable=no-value-for-parameter

    def test_name_property_returns_settings_value(self):
        """container.name delegates to settings.pyball.name."""
        settings = MagicMock()
        settings.pyball.name = "Tensores"
        container = Container(settings)
        assert container.name == "Tensores"


class TestContainerAddRemovePlayerById:
    """Tests for Container wiring of the ID-based join/leave use cases."""

    def test_add_player_to_meetup_by_id_returns_use_case(self):
        """add_player_to_meetup_by_id returns a use case wired to the meetup repository."""
        settings = MagicMock()
        container = Container(settings)
        use_case = container.add_player_to_meetup_by_id()
        assert isinstance(use_case, AddPlayerToMeetupById)
        assert use_case.meetup_repository is container.meetup_repository

    def test_remove_player_from_meetup_by_id_returns_use_case(self):
        """remove_player_from_meetup_by_id returns a use case wired to the meetup repository."""
        settings = MagicMock()
        container = Container(settings)
        use_case = container.remove_player_from_meetup_by_id()
        assert isinstance(use_case, RemovePlayerFromMeetupById)
        assert use_case.meetup_repository is container.meetup_repository


class TestContainerSignupLinkBuilder:
    """Tests for Container wiring of the signup link builder."""

    def test_signup_link_builder_uses_base_url_and_token(self):
        """signup_link_builder returns a SignupLinkBuilder wired to base_url and signup_token."""
        settings = MagicMock()
        settings.pyball.base_url = "http://pyball:8000"
        settings.pyball.signup_token = "tok-456"
        container = Container(settings)
        builder = container.signup_link_builder()
        assert isinstance(builder, SignupLinkBuilder)
        assert builder.build() == "http://pyball:8000/signup?token=tok-456"
