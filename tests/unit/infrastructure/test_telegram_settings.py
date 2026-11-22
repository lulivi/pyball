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

import logging
from pathlib import Path

import pytest

from pyball.infrastructure.telegram.settings import (
    ChatConfig,
    RegularsChats,
    SubstitutesChats,
    TelegramAppSettings,
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

[pyball.telegram.regulars.meetups]
chat_id = -100111

[pyball.telegram.regulars.stats]
chat_id = -100111

[pyball.telegram.substitutes.meetups]
chat_id = -100222
"""


def _base(tmp_path: Path) -> AppSettings:
    from pyball.settings import load_app_settings

    return load_app_settings(_write_config(tmp_path, _MINIMAL_CONFIG))


class TestChatConfig:
    """Tests for the ChatConfig value object."""

    def test_defaults_to_disabled(self):
        """A default ChatConfig has no chat and no topic."""
        cfg = ChatConfig()
        assert cfg.chat_id == 0
        assert cfg.message_thread_id is None

    def test_is_falsy_when_chat_id_is_zero(self):
        """bool(ChatConfig) is False when no chat is configured."""
        assert not ChatConfig()
        assert not ChatConfig(message_thread_id=5)

    def test_is_truthy_when_chat_id_is_set(self):
        """bool(ChatConfig) is True once chat_id is non-zero."""
        assert ChatConfig(chat_id=-100123)

    def test_keeps_message_thread_id(self):
        """message_thread_id is stored as given."""
        assert ChatConfig(chat_id=-1, message_thread_id=27246).message_thread_id == 27246


class TestTelegramSettings:
    """Tests for TelegramSettings dataclass."""

    def test_is_authorized_true_for_admin(self):
        """User ID in admins_ids is authorized."""
        assert TelegramSettings(admins_ids=(10, 20)).is_authorized(10) is True

    def test_is_authorized_false_for_non_admin(self):
        """User ID not in admins_ids is not authorized."""
        assert TelegramSettings(admins_ids=(10, 20)).is_authorized(99) is False

    def test_is_authorized_false_when_empty(self):
        """Empty admins_ids means no one is authorized."""
        assert TelegramSettings().is_authorized(1) is False

    def test_default_tree_is_all_disabled_chat_configs(self):
        """A default TelegramSettings has every leaf as a falsy ChatConfig."""
        s = TelegramSettings()
        assert isinstance(s.regulars, RegularsChats)
        assert isinstance(s.substitutes, SubstitutesChats)
        for leaf in (
            s.regulars.meetups,
            s.regulars.stats,
            s.substitutes.meetups,
        ):
            assert isinstance(leaf, ChatConfig)
            assert not leaf


class TestTelegramAppSettings:
    """Tests for TelegramAppSettings dataclass."""

    def test_is_subtype_of_app_settings(self, tmp_path):
        """TelegramAppSettings is an AppSettings."""
        base = _base(tmp_path)
        settings = load_telegram_app_settings(base, _write_config(tmp_path, _MINIMAL_CONFIG))
        assert isinstance(settings, AppSettings)

    def test_carries_pyball_and_paths(self, tmp_path):
        """Inherited pyball and paths fields are accessible."""
        base = _base(tmp_path)
        settings = load_telegram_app_settings(base, _write_config(tmp_path, _MINIMAL_CONFIG))
        assert settings.pyball.location == "Test Park"


class TestLoadTelegramAppSettings:
    """Tests for load_telegram_app_settings."""

    def _load(self, tmp_path, config=_MINIMAL_CONFIG):
        base = _base(tmp_path)
        return load_telegram_app_settings(base, _write_config(tmp_path, config))

    def test_loads_bot_token_and_admins(self, tmp_path):
        """bot_token and admins_ids are read from config."""
        s = self._load(tmp_path).telegram
        assert s.bot_token == "tok"
        assert s.admins_ids == (1,)

    def test_loads_required_chat_ids(self, tmp_path):
        """regulars.meetups, regulars.stats and substitutes.meetups chat ids load."""
        s = self._load(tmp_path).telegram
        assert s.regulars.meetups.chat_id == -100111
        assert s.regulars.stats.chat_id == -100111
        assert s.substitutes.meetups.chat_id == -100222

    def test_leaves_default_to_disabled_when_section_absent(self, tmp_path):
        """An optional message_thread_id defaults to no topic when not in the file."""
        s = self._load(tmp_path).telegram
        assert s.regulars.meetups.message_thread_id is None

    def test_parses_message_thread_id_as_int(self, tmp_path):
        """message_thread_id is parsed to int from a quoted string."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\n",
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\nmessage_thread_id = '77'\n",
        )
        s = self._load(tmp_path, config).telegram
        assert s.regulars.meetups.message_thread_id == 77

    def test_zero_message_thread_id_is_none(self, tmp_path):
        """message_thread_id = 0 means no topic, never a literal 0."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\n",
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\nmessage_thread_id = 0\n",
        )
        s = self._load(tmp_path, config).telegram
        assert s.regulars.meetups.message_thread_id is None

    def test_empty_message_thread_id_is_none(self, tmp_path):
        """message_thread_id = '' means no topic."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\n",
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\nmessage_thread_id = ''\n",
        )
        s = self._load(tmp_path, config).telegram
        assert s.regulars.meetups.message_thread_id is None

    def test_env_override_nested_chat_id(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_SUBSTITUTES_MEETUPS_CHAT_ID overrides config."""
        monkeypatch.setenv("PYBALL_TELEGRAM_SUBSTITUTES_MEETUPS_CHAT_ID", "-100444")
        s = self._load(tmp_path).telegram
        assert s.substitutes.meetups.chat_id == -100444

    def test_env_override_nested_message_thread_id(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_REGULARS_MEETUPS_MESSAGE_THREAD_ID overrides config."""
        monkeypatch.setenv("PYBALL_TELEGRAM_REGULARS_MEETUPS_MESSAGE_THREAD_ID", "999")
        s = self._load(tmp_path).telegram
        assert s.regulars.meetups.message_thread_id == 999

    def test_env_override_bot_token(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_BOT_TOKEN overrides config value."""
        monkeypatch.setenv("PYBALL_TELEGRAM_BOT_TOKEN", "env_tok")
        assert self._load(tmp_path).telegram.bot_token == "env_tok"

    def test_env_override_admins_ids(self, tmp_path, monkeypatch):
        """PYBALL_TELEGRAM_ADMINS_IDS comma-separated overrides config."""
        monkeypatch.setenv("PYBALL_TELEGRAM_ADMINS_IDS", "5,6,7")
        assert self._load(tmp_path).telegram.admins_ids == (5, 6, 7)

    def test_missing_config_file_raises(self, tmp_path):
        """Missing config file raises SettingsValidationError immediately."""
        with pytest.raises(SettingsValidationError, match="No se encontró"):
            load_telegram_app_settings(_base(tmp_path), tmp_path / "nonexistent.toml")

    def test_missing_bot_token_raises(self, tmp_path):
        """Empty bot_token raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace('bot_token = "tok"', 'bot_token = ""')
        with pytest.raises(SettingsValidationError, match="telegram.bot_token"):
            self._load(tmp_path, config)

    def test_missing_admins_ids_raises(self, tmp_path):
        """Empty admins_ids raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace("admins_ids = [1]", "admins_ids = []")
        with pytest.raises(SettingsValidationError, match="admins_ids"):
            self._load(tmp_path, config)

    def test_missing_regulars_meetups_chat_id_raises(self, tmp_path):
        """Missing regulars.meetups.chat_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.meetups]\nchat_id = -100111\n", ""
        )
        with pytest.raises(SettingsValidationError, match="regulars.meetups.chat_id"):
            self._load(tmp_path, config)

    def test_missing_substitutes_meetups_chat_id_raises(self, tmp_path):
        """Missing substitutes.meetups.chat_id raises SettingsValidationError."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.substitutes.meetups]\nchat_id = -100222\n", ""
        )
        with pytest.raises(SettingsValidationError, match="substitutes.meetups.chat_id"):
            self._load(tmp_path, config)

    def test_regulars_stats_is_optional(self, tmp_path):
        """Absent regulars.stats section is allowed and yields a disabled ChatConfig."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.stats]\nchat_id = -100111\n", ""
        )
        assert not self._load(tmp_path, config).telegram.regulars.stats

    def test_warns_when_regulars_stats_unconfigured(self, tmp_path, caplog):
        """A minimal (but valid) config without regulars.stats warns at load time."""
        config = _MINIMAL_CONFIG.replace(
            "[pyball.telegram.regulars.stats]\nchat_id = -100111\n", ""
        )
        with caplog.at_level(logging.WARNING, logger="pyball.infrastructure.telegram.settings"):
            self._load(tmp_path, config)
        assert any("telegram.regulars.stats no está configurado" in m for m in caplog.messages)

    def test_no_warning_when_regulars_stats_configured(self, tmp_path, caplog):
        """A config with regulars.stats set does not emit the stats warning."""
        with caplog.at_level(logging.WARNING, logger="pyball.infrastructure.telegram.settings"):
            self._load(tmp_path)
        assert not any("telegram.regulars.stats no está configurado" in m for m in caplog.messages)
