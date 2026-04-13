"""Tests for settings loading and validation."""

import pytest

from pyball.settings import (
    LocaleSettings,
    RegularsChatSettings,
    SettingsValidationError,
    TelegramChatSettings,
    TelegramSettings,
    load_settings,
)


class TestTelegramSettings:
    """Tests for TelegramSettings authorization logic."""

    def test_is_authorized_returns_true_for_admin(self):
        """A user ID in the admins list is authorized."""
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(123) is True
        assert settings.is_authorized(456) is True
        assert settings.is_authorized(789) is True

    def test_is_authorized_returns_false_for_non_admin(self):
        """A user ID not in the admins list is not authorized."""
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(999) is False

    def test_is_authorized_returns_false_for_empty_list(self):
        """No admins configured means no one is authorized."""
        settings = TelegramSettings(admins_ids=())
        assert settings.is_authorized(123) is False

    def test_substitutes_has_no_stats_thread_id(self):
        """Substitutes settings do not have a stats_thread_id attribute."""
        subs = TelegramChatSettings(chat_id=123, meetups_thread_id="")
        assert not hasattr(subs, "stats_thread_id")

    def test_regulars_chat_settings_is_subclass_of_telegram_chat_settings(self):
        """RegularsChatSettings is a subclass of TelegramChatSettings."""
        assert issubclass(RegularsChatSettings, TelegramChatSettings)


class TestLocaleSettings:
    """Tests for LocaleSettings defaults and customisation."""

    def test_default_locale(self):
        """Default locale is en_US.UTF-8."""
        locale = LocaleSettings()
        assert locale.value == "en_US.UTF-8"

    def test_custom_locale(self):
        """A custom locale value is stored as-is."""
        locale = LocaleSettings(value="es_ES.UTF-8")
        assert locale.value == "es_ES.UTF-8"


class TestLoadSettings:
    """Tests for load_settings reading config files and env-var overrides."""

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

    def test_meetups_thread_id_loaded_from_config(self, tmp_path):
        """meetups_thread_id is read from config."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
meetups_thread_id = "42"

[telegram.substitutes]
chat_id = -1001234567891
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        settings = load_settings(config_file)
        assert settings.telegram.regulars.meetups_thread_id == "42"

    def test_stats_thread_id_loaded_from_config(self, tmp_path):
        """stats_thread_id is read from config for regulars."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
stats_thread_id = "99"

[telegram.substitutes]
chat_id = -1001234567891
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        settings = load_settings(config_file)
        assert settings.telegram.regulars.stats_thread_id == "99"

    def test_stats_thread_id_defaults_to_empty(self, tmp_path):
        """stats_thread_id is empty string when not configured."""
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
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        settings = load_settings(config_file)
        assert settings.telegram.regulars.stats_thread_id == ""
        assert settings.telegram.regulars.has_stats_thread() is False

    def test_has_stats_thread_true_when_set(self, tmp_path):
        """has_stats_thread() returns True when stats_thread_id is set."""
        config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890
stats_thread_id = "55"

[telegram.substitutes]
chat_id = -1001234567891
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        settings = load_settings(config_file)
        assert settings.telegram.regulars.has_stats_thread() is True

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
