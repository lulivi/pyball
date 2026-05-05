"""Unit tests for Container."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyball.application.container import Container


class TestContainerInit:
    """Tests for Container.__init__."""

    def test_stores_injected_settings(self):
        """Container stores the injected settings object."""
        settings = MagicMock()
        container = Container(settings)
        assert container._settings is settings  # pylint: disable=protected-access

    def test_legacy_stats_path_uses_settings_data_dir(self, tmp_path):
        """legacy_stats uses settings.paths.data_dir to locate the file."""
        (tmp_path / "legacy_stats.json").write_text("{}")
        settings = MagicMock()
        settings.paths.data_dir = tmp_path
        container = Container(settings)
        _ = container.legacy_stats
        assert container._legacy_stats is not None  # pylint: disable=protected-access

    def test_no_data_dir_parameter(self):
        """Container rejects unknown keyword arguments."""
        settings = MagicMock()
        with pytest.raises(TypeError):
            Container(  # type: ignore[call-arg]  # pylint: disable=unexpected-keyword-arg
                settings, data_dir=Path("/tmp")
            )
