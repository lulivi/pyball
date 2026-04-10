import pytest
from unittest.mock import patch
from pathlib import Path
from pyball.settings import (
    Settings,
    TelegramSettings,
    LocaleSettings,
    load_settings,
    SettingsValidationError,
)


class TestTelegramSettings:
    def test_is_authorized_returns_true_for_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(123) is True
        assert settings.is_authorized(456) is True
        assert settings.is_authorized(789) is True

    def test_is_authorized_returns_false_for_non_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(999) is False

    def test_is_authorized_returns_false_for_empty_list(self):
        settings = TelegramSettings(admins_ids=())
        assert settings.is_authorized(123) is False


class TestLocaleSettings:
    def test_default_locale(self):
        locale = LocaleSettings()
        assert locale.value == "en_US.UTF-8"

    def test_custom_locale(self):
        locale = LocaleSettings(value="es_ES.UTF-8")
        assert locale.value == "es_ES.UTF-8"


class TestLoadSettings:
    def test_load_from_config_file(self, tmp_path):
        """Test loading settings from config.toml file."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111, 222]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891

[locale]
value = "es_ES.UTF-8"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        settings = load_settings(config_file)
        
        assert settings.telegram.bot_token == "test_token"
        assert settings.telegram.admins_ids == (111, 222)
        assert settings.pyball.location == "Test Park"
        assert settings.locale.value == "es_ES.UTF-8"

    def test_env_override_bot_token(self, tmp_path, monkeypatch):
        """Test that env vars override config file values."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "config_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891

[locale]
value = "en_US.UTF-8"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        monkeypatch.setenv("PYBALL_TELEGRAM_BOT_TOKEN", "env_token")
        
        settings = load_settings(config_file)
        
        assert settings.telegram.bot_token == "env_token"

    def test_env_override_admins_ids_comma_separated(self, tmp_path, monkeypatch):
        """Test comma-separated env var for admins_ids."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891

[locale]
value = "en_US.UTF-8"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        monkeypatch.setenv("PYBALL_TELEGRAM_ADMINS_IDS", "333,444,555")
        
        settings = load_settings(config_file)
        
        assert settings.telegram.admins_ids == (333, 444, 555)

    def test_missing_bot_token_raises_error(self, tmp_path):
        """Test that missing bot_token raises SettingsValidationError."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = ""
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891

[locale]
value = "en_US.UTF-8"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        with pytest.raises(SettingsValidationError):
            load_settings(config_file)
