"""Unit tests for Container."""

from unittest.mock import MagicMock, patch

import pytest

from pyball.application.container import Container


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
