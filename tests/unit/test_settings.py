"""Tests for settings loading and validation."""

import pytest

from pyball.settings import AppSettings, PyballConfig, SettingsValidationError, load_app_settings


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
    """Tests for load_app_settings — validates only pyball.location."""

    def test_load_from_config_file(self, tmp_path):
        """Loads pyball.core section; does not require telegram credentials."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[pyball.core]\nlocation = 'Test Park'\n")
        settings = load_app_settings(config_file)
        assert settings.pyball.location == "Test Park"
        assert isinstance(settings, AppSettings)

    def test_missing_location_raises(self, tmp_path):
        """Empty location raises SettingsValidationError."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[pyball.core]\n")
        with pytest.raises(SettingsValidationError):
            load_app_settings(config_file)

    def test_env_override_location(self, tmp_path, monkeypatch):
        """PYBALL_CORE_LOCATION env var sets location."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        monkeypatch.setenv("PYBALL_CORE_LOCATION", "Env Park")
        settings = load_app_settings(config_file)
        assert settings.pyball.location == "Env Park"

    def test_team_display_names_default(self, tmp_path):
        """team_display_names defaults to ('Claro', 'Oscuro')."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[pyball.core]\nlocation = 'Park'\n")
        settings = load_app_settings(config_file)
        assert settings.pyball.team_display_names == ("Claro", "Oscuro")

    def test_team_display_names_from_config(self, tmp_path):
        """team_display_names is read from config when set."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[pyball.core]\nlocation = 'Park'\nteam_display_names = ['Blancos', 'Negros']\n"
        )
        settings = load_app_settings(config_file)
        assert settings.pyball.team_display_names == ("Blancos", "Negros")

    def test_display_date_format_from_config(self, tmp_path):
        """display_date_format is read from config when set."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[pyball.core]\nlocation = 'Park'\ndisplay_date_format = '%d/%m/%Y %H:%M'\n"
        )
        settings = load_app_settings(config_file)
        assert settings.pyball.display_date_format == "%d/%m/%Y %H:%M"
