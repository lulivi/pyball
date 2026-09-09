# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Tests for Telegram-specific settings and loader."""

from pathlib import Path

import pytest

from pyball.infrastructure.telegram.settings import (
    ActivityChatSettings,
    ManagementChatSettings,
    RegularsChatSettings,
    TelegramAppSettings,
    TelegramChatSettings,
    TelegramSettings,
    load_telegram_app_settings,
)
from pyball.settings import AppSettings, SettingsValidationError


def _write_config(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "config.toml"
    f.write_text(content)
    return f


_MINIMAL_CONFIG = """
[pyball.core]
name = "TestApp"
location = "Test Park"
default_week_day = "wednesday"
default_hour = "20:00"
base_url = "http://localhost:8000"
team_colors = ["blanco", "negro"]
locale = "en_US.UTF-8"
display_date_format = "%Y-%m-%d %H:%M"
data_dir = "data"
api_port = 8000

[pyball.telegram]
bot_token = "tok"
admins_ids = [1]

[pyball.telegram.regulars]
chat_id = -100111
meetups_thread_id = ""
stats_thread_id = ""

[pyball.telegram.substitutes]
chat_id = -100222

[pyball.telegram.management]
chat_id = 0
"""


def _base(tmp_path: Path) -> AppSettings:
    from pyball.settings import load_app_settings

    return load_app_settings(_write_config(tmp_path, _MINIMAL_CONFIG))


class TestTelegramSettings:
    """Tests for TelegramSettings dataclass."""

    def test_is_authorized_true_for_admin(self):
        """User ID in admins_ids is authorized."""
        s = TelegramSettings(admins_ids=(10, 20))
        assert s.is_authorized(10) is True

    def test_is_authorized_false_for_non_admin(self):
        """User ID not in admins_ids is not authorized."""
        s = TelegramSettings(admins_ids=(10, 20))
        assert s.is_authorized(99) is False

    def test_is_authorized_false_when_empty(self):
        """Empty admins_ids means no one is authorized."""
        assert TelegramSettings().is_authorized(1) is False

    def test_regulars_is_subclass_of_telegram_chat_settings(self):
        """RegularsChatSettings inherits TelegramChatSettings."""
        assert issubclass(RegularsChatSettings, TelegramChatSettings)

    def test_management_is_subclass_of_telegram_chat_settings(self):
        """ManagementChatSettings inherits TelegramChatSettings."""
        assert issubclass(ManagementChatSettings, TelegramChatSettings)

    def test_management_has_no_thread_ids(self):
        """ManagementChatSettings has only chat_id."""
        m = ManagementChatSettings(chat_id=-1)
        assert not hasattr(m, "meetups_thread_id")

    def test_activity_is_subclass_of_telegram_chat_settings(self):
        """ActivityChatSettings inherits TelegramChatSettings."""
        assert issubclass(ActivityChatSettings, TelegramChatSettings)

    def test_activity_defaults_to_disabled(self):
        """ActivityChatSettings defaults to chat_id=0 and empty thread_id."""
        activity = ActivityChatSettings()
        assert activity.chat_id == 0
        assert activity.thread_id == ""


class TestTelegramAppSettings:
    """Tests for TelegramAppSettings dataclass."""

    def test_is_subtype_of_app_settings(self, tmp_path):
        """TelegramAppSettings is an AppSettings."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert isinstance(settings, AppSettings)

    def test_carries_pyball_and_paths(self, tmp_path):
        """Inherited pyball and paths fields are accessible."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.pyball.location == "Test Park"


class TestLoadTelegramAppSettings:
    """Tests for load_telegram_app_settings."""

    def test_loads_bot_token(self, tmp_path):
        """bot_token is read from config."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.bot_token == "tok"

    def test_loads_admins_ids(self, tmp_path):
        """admins_ids is read from config."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.admins_ids == (1,)

    def test_loads_regulars_chat_id(self, tmp_path):
        """regulars.chat_id is read from config."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.regulars.chat_id == -100111

    def test_loads_substitutes_chat_id(self, tmp_path):
        """substitutes.chat_id is read from config."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.substitutes.chat_id == -100222

    def test_activity_chat_id_defaults_to_zero_when_absent(self, tmp_path):
        """activity.chat_id defaults to 0 (disabled) when the section is absent."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.activity.chat_id == 0
        assert settings.telegram.activity.thread_id == ""

    def test_loads_activity_chat_id_and_thread_id(self, tmp_path):
        """activity.chat_id and activity.thread_id are read from config when present."""
        config = _MINIMAL_CONFIG + (
            "\n[pyball.telegram.activity]\nchat_id = -100333\nthread_id = '9'\n"
        )
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.activity.chat_id == -100333
        assert settings.telegram.activity.thread_id == "9"

    def test_env_override_activity_chat_id(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_ACTIVITY_CHAT_ID overrides config value."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        monkeypatch.setenv("PYBALL_TELEGRAM_ACTIVITY_CHAT_ID", "-100444")
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.activity.chat_id == -100444

    def test_management_chat_id_zero_is_valid(self, tmp_path):
        """management.chat_id = 0 is valid (means disabled)."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.management.chat_id == 0

    def test_missing_management_chat_id_raises(self, tmp_path):
        """Absent management.chat_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace("\n[pyball.telegram.management]\nchat_id = 0\n", "")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError, match="management.chat_id"):
            load_telegram_app_settings(base, cfg)

    def test_missing_meetups_thread_id_raises(self, tmp_path):
        """Absent meetups_thread_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace('meetups_thread_id = ""\n', "")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError, match="meetups_thread_id"):
            load_telegram_app_settings(base, cfg)

    def test_missing_stats_thread_id_raises(self, tmp_path):
        """Absent stats_thread_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace('stats_thread_id = ""\n', "")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError, match="stats_thread_id"):
            load_telegram_app_settings(base, cfg)

    def test_loads_management_chat_id(self, tmp_path):
        """management.chat_id is read when present."""
        config = _MINIMAL_CONFIG.replace("chat_id = 0", "chat_id = -999")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.management.chat_id == -999

    def test_loads_thread_ids(self, tmp_path):
        """meetups_thread_id and stats_thread_id are read from config."""
        config = _MINIMAL_CONFIG.replace(
            'meetups_thread_id = ""\nstats_thread_id = ""',
            "meetups_thread_id = '42'\nstats_thread_id = '7'",
        )
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.regulars.meetups_thread_id == "42"
        assert settings.telegram.regulars.stats_thread_id == "7"

    def test_missing_config_file_raises(self, tmp_path):
        """Missing config file raises SettingsValidationError immediately."""
        base = _base(tmp_path)
        with pytest.raises(SettingsValidationError, match="No se encontró"):
            load_telegram_app_settings(base, tmp_path / "nonexistent.toml")

    def test_missing_bot_token_raises(self, tmp_path):
        """Empty bot_token raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace('bot_token = "tok"', 'bot_token = ""')
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError):
            load_telegram_app_settings(base, cfg)

    def test_missing_admins_ids_raises(self, tmp_path):
        """Empty admins_ids raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace("admins_ids = [1]", "admins_ids = []")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError, match="admins_ids"):
            load_telegram_app_settings(base, cfg)

    def test_missing_regulars_chat_id_raises(self, tmp_path):
        """Missing regulars.chat_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace("chat_id = -100111", "chat_id = 0")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError):
            load_telegram_app_settings(base, cfg)

    def test_missing_substitutes_chat_id_raises(self, tmp_path):
        """Missing substitutes.chat_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace("chat_id = -100222", "chat_id = 0")
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, config)
        with pytest.raises(SettingsValidationError):
            load_telegram_app_settings(base, cfg)

    def test_env_override_bot_token(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_BOT_TOKEN overrides config value."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        monkeypatch.setenv("PYBALL_TELEGRAM_BOT_TOKEN", "env_tok")
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.bot_token == "env_tok"

    def test_env_override_admins_ids(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_ADMINS_IDS comma-separated overrides config."""
        base = _base(tmp_path)
        cfg = _write_config(tmp_path, _MINIMAL_CONFIG)
        monkeypatch.setenv("PYBALL_TELEGRAM_ADMINS_IDS", "5,6,7")
        settings = load_telegram_app_settings(base, cfg)
        assert settings.telegram.admins_ids == (5, 6, 7)
