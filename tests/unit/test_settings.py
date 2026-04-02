import os
import pytest
from pyball.settings import TelegramSettings


class TestTelegramSettings:
    def test_is_authorized_returns_true_for_admin(self):
        settings = TelegramSettings(bot_token="test_token", admins_ids=(123, 456, 789))
        assert settings.is_authorized(123) is True
        assert settings.is_authorized(456) is True
        assert settings.is_authorized(789) is True

    def test_is_authorized_returns_false_for_non_admin(self):
        settings = TelegramSettings(bot_token="test_token", admins_ids=(123, 456, 789))
        assert settings.is_authorized(999) is False

    def test_is_authorized_returns_false_for_empty_list(self):
        settings = TelegramSettings(bot_token="test_token", admins_ids=())
        assert settings.is_authorized(123) is False

    def test_admins_ids_parsed_from_env(self, monkeypatch):
        monkeypatch.setenv("admins_ids", "100, 200, 300")
        settings = TelegramSettings(bot_token="test_token")
        assert settings.admins_ids == (100, 200, 300)
