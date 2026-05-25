"""Tests for settings loading and validation."""

import pytest

from pyball.settings import (
    COLOR_PALETTE,
    AppSettings,
    PyballConfig,
    SettingsValidationError,
    load_app_settings,
)

_FULL_CORE = """\
[pyball.core]
location = "Test Park"
default_week_day = "wednesday"
default_hour = "20:00"
base_url = "http://localhost:8000"
team_colors = ["blanco", "negro"]
locale = "en_US.UTF-8"
display_date_format = "%Y-%m-%d %H:%M"
data_dir = "data"
api_port = 8000
"""


def _write(tmp_path, content: str):
    f = tmp_path / "config.toml"
    f.write_text(content)
    return f


class TestLocaleSettings:
    """Tests for LocaleSettings defaults and customisation."""

    def test_default_locale(self):
        """Default locale is en_US.UTF-8."""
        settings = PyballConfig()
        assert settings.locale == "en_US.UTF-8"

    def test_custom_locale(self):
        """A custom locale value is stored as-is."""
        settings = PyballConfig(locale="es_ES.UTF-8")
        assert settings.locale == "es_ES.UTF-8"

    def test_default_display_date_format(self):
        """Default display_date_format is %Y-%m-%d %H:%M."""
        settings = PyballConfig()
        assert settings.display_date_format == "%Y-%m-%d %H:%M"

    def test_custom_display_date_format(self):
        """A custom display_date_format value is stored as-is."""
        settings = PyballConfig(display_date_format="%d/%b/%Y %H:%M")
        assert settings.display_date_format == "%d/%b/%Y %H:%M"


class TestLoadAppSettings:
    """Tests for load_app_settings — all core fields are required."""

    def test_load_from_config_file(self, tmp_path):
        """Loads pyball.core section with all required fields present."""
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.location == "Test Park"
        assert isinstance(settings, AppSettings)

    def test_missing_config_file_raises(self, tmp_path):
        """Missing config.toml raises SettingsValidationError immediately."""
        with pytest.raises(SettingsValidationError, match="No se encontró"):
            load_app_settings(tmp_path / "nonexistent.toml")

    def test_missing_location_raises(self, tmp_path):
        """Absent location raises SettingsValidationError."""
        config = _FULL_CORE.replace('location = "Test Park"\n', "")
        with pytest.raises(SettingsValidationError, match="core.location"):
            load_app_settings(_write(tmp_path, config))

    def test_missing_any_field_raises(self, tmp_path):
        """Absent required field raises SettingsValidationError listing the key."""
        config = _FULL_CORE.replace('default_week_day = "wednesday"\n', "")
        with pytest.raises(SettingsValidationError, match="core.default_week_day"):
            load_app_settings(_write(tmp_path, config))

    def test_env_override_location(self, tmp_path, monkeypatch):
        """PYBALL_CORE_LOCATION env var counts as providing the field."""
        config = _FULL_CORE.replace('location = "Test Park"\n', "")
        monkeypatch.setenv("PYBALL_CORE_LOCATION", "Env Park")
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.location == "Env Park"

    def test_team_colors_required(self, tmp_path):
        """Omitting team_colors raises SettingsValidationError."""
        config = _FULL_CORE.replace('team_colors = ["blanco", "negro"]\n', "")
        with pytest.raises(SettingsValidationError, match="core.team_colors"):
            load_app_settings(_write(tmp_path, config))

    def test_team_colors_from_config(self, tmp_path):
        """team_colors is loaded from config and resolved correctly."""
        config = _FULL_CORE.replace(
            'team_colors = ["blanco", "negro"]',
            'team_colors = ["amarillo", "negro"]',
        )
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.team_colors == ("amarillo", "negro")
        assert settings.pyball.team_emojis == ("🟡", "⚫")
        assert settings.pyball.team_hex_bg == ("#fbbf24", "#27272a")

    def test_display_date_format_from_config(self, tmp_path):
        """display_date_format is read from config when set."""
        config = _FULL_CORE.replace(
            'display_date_format = "%Y-%m-%d %H:%M"',
            'display_date_format = "%d/%m/%Y %H:%M"',
        )
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.display_date_format == "%d/%m/%Y %H:%M"


class TestPyballConfigColors:
    """Unit tests for PyballConfig team color resolution."""

    def test_default_team_colors(self):
        """Default team_colors is ('blanco', 'negro')."""
        s = PyballConfig()
        assert s.team_colors == ("blanco", "negro")

    def test_default_resolves_emojis(self):
        """Default colors resolve to white and black circle emojis."""
        s = PyballConfig()
        assert s.team_emojis == ("⚪", "⚫")

    def test_default_resolves_hex_bg(self):
        """Default colors resolve to correct background hex values."""
        s = PyballConfig()
        assert s.team_hex_bg == ("#e4e4e7", "#27272a")

    def test_default_resolves_hex_text(self):
        """Default colors resolve to correct text hex values."""
        s = PyballConfig()
        assert s.team_hex_text == ("#27272a", "#e4e4e7")

    def test_custom_colors_resolve_correctly(self):
        """Custom team_colors resolve to the correct palette values."""
        s = PyballConfig(team_colors=("amarillo", "negro"))
        assert s.team_emojis == ("🟡", "⚫")
        assert s.team_hex_bg == ("#fbbf24", "#27272a")
        assert s.team_hex_text == ("#422006", "#e4e4e7")

    def test_invalid_color_raises_value_error(self):
        """An unknown color name raises ValueError at construction time."""
        with pytest.raises(ValueError, match="inventado"):
            PyballConfig(team_colors=("azul", "inventado"))

    def test_all_palette_colors_are_valid(self):
        """Every color in COLOR_PALETTE can be used without raising."""
        for color in COLOR_PALETTE:
            PyballConfig(team_colors=(color, "negro"))
