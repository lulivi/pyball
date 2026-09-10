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
"""Tests for Telegram logging handler and config function."""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from pyball.infrastructure.telegram.logging import (
    TelegramLogHandler,
    _ManagementFilter,
    config_telegram_logging,
)
from pyball.infrastructure.telegram.settings import ChatConfig, ManagementChats, TelegramSettings


class TestManagementFilter:
    """Tests for _ManagementFilter."""

    def setup_method(self):
        """Create a fresh filter for each test."""
        self.f = _ManagementFilter()  # pylint: disable=attribute-defined-outside-init

    def _record(self, name: str, level: int) -> logging.LogRecord:
        return logging.LogRecord(
            name=name, level=level, pathname="", lineno=1, msg="msg", args=(), exc_info=None
        )

    def test_pyball_info_passes(self):
        """pyball.* at INFO is forwarded."""
        assert self.f.filter(self._record("pyball.bot", logging.INFO))

    def test_pyball_debug_blocked(self):
        """pyball.* at DEBUG is NOT forwarded."""
        assert not self.f.filter(self._record("pyball.domain", logging.DEBUG))

    def test_telegram_error_passes(self):
        """telegram at ERROR is forwarded."""
        assert self.f.filter(self._record("telegram", logging.ERROR))

    def test_telegram_ext_error_passes(self):
        """telegram.ext at ERROR is forwarded."""
        assert self.f.filter(self._record("telegram.ext", logging.ERROR))

    def test_telegram_warning_blocked(self):
        """telegram at WARNING is NOT forwarded."""
        assert not self.f.filter(self._record("telegram", logging.WARNING))

    def test_httpx_info_blocked(self):
        """httpx at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("httpx", logging.INFO))

    def test_root_logger_blocked(self):
        """Root logger at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("", logging.INFO))

    def test_pyball_root_blocked(self):
        """'pyball' without dot suffix at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("pyball", logging.INFO))

    def test_telegramfoo_blocked(self):
        """'telegramfoo' (no dot) at ERROR is NOT forwarded."""
        assert not self.f.filter(self._record("telegramfoo", logging.ERROR))


class TestTelegramLogHandler:
    """Tests for TelegramLogHandler.emit()."""

    _PATCH = "pyball.infrastructure.telegram.logging.urllib.request.urlopen"

    def _make_record(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        name: str = "pyball.bot",
        level: int = logging.INFO,
        lineno: int = 42,
        msg: str = "test message",
        exc_info=None,
    ) -> logging.LogRecord:
        return logging.LogRecord(
            name=name,
            level=level,
            pathname="",
            lineno=lineno,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )

    def _payload(self, mock_urlopen) -> dict:
        return json.loads(mock_urlopen.call_args.args[0].data)

    def test_posts_to_correct_url(self):
        """emit() uses the configured token in the sendMessage URL."""
        handler = TelegramLogHandler("mytoken", -100111)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert m.call_args.args[0].full_url == "https://api.telegram.org/botmytoken/sendMessage"

    def test_sends_chat_id(self):
        """emit() includes chat_id in the payload."""
        handler = TelegramLogHandler("tok", -100999)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["chat_id"] == -100999

    def test_uses_markdownv2(self):
        """emit() sets parse_mode to MarkdownV2."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["parse_mode"] == "MarkdownV2"

    def test_info_emoji(self):
        """INFO records use the ℹ️ emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.INFO))
        assert "ℹ️" in self._payload(m)["text"]

    def test_warning_emoji(self):
        """WARNING records use the ⚠️ emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.WARNING))
        assert "⚠️" in self._payload(m)["text"]

    def test_error_emoji(self):
        """ERROR records use the 🔴 emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.ERROR))
        assert "🔴" in self._payload(m)["text"]

    def test_critical_emoji(self):
        """CRITICAL records use the 💀 emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.CRITICAL))
        assert "💀" in self._payload(m)["text"]

    def test_includes_message(self):
        """Text contains the log message."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(msg="something broke"))
        assert "something broke" in self._payload(m)["text"]

    def test_includes_traceback(self):
        """Text includes the traceback when exc_info is present."""
        handler = TelegramLogHandler("tok", -1)
        try:
            raise ValueError("kaboom")
        except ValueError:
            exc_info = sys.exc_info()
        record = self._make_record(level=logging.ERROR, exc_info=exc_info)
        with patch(self._PATCH) as m:
            handler.emit(record)
        text = self._payload(m)["text"]
        assert "ValueError" in text
        assert "kaboom" in text

    def test_wraps_in_code_block(self):
        """Text is wrapped in a MarkdownV2 code block."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        text = self._payload(m)["text"]
        assert "```" in text
        assert text.endswith("\n```")

    def test_silences_network_exception(self):
        """Network errors in emit() call handleError, not propagate."""
        handler = TelegramLogHandler("tok", -1)
        mock_handle_error = MagicMock()
        setattr(handler, "handleError", mock_handle_error)
        record = self._make_record()
        with patch(self._PATCH) as m:
            m.side_effect = OSError("network down")
            handler.emit(record)
        mock_handle_error.assert_called_once_with(record)

    def test_includes_message_thread_id_when_set(self):
        """emit() adds message_thread_id to the payload when configured."""
        handler = TelegramLogHandler("tok", -100999, message_thread_id=77)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["message_thread_id"] == 77

    def test_omits_message_thread_id_when_none(self):
        """emit() leaves message_thread_id out of the payload when not configured."""
        handler = TelegramLogHandler("tok", -100999)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert "message_thread_id" not in self._payload(m)


class TestConfigTelegramLogging:
    """Tests for config_telegram_logging."""

    def test_adds_handler_when_chat_id_set(self):
        """config_telegram_logging adds a TelegramLogHandler to the root logger."""
        tg = TelegramSettings(
            bot_token="tok",
            management=ManagementChats(logging=ChatConfig(chat_id=-100111)),
        )
        root_logger = logging.getLogger()
        before = list(root_logger.handlers)
        try:
            config_telegram_logging(tg)
            new_handlers = [h for h in root_logger.handlers if h not in before]
            assert any(isinstance(h, TelegramLogHandler) for h in new_handlers)
        finally:
            for h in root_logger.handlers[:]:
                if h not in before:
                    root_logger.removeHandler(h)

    def test_does_not_add_handler_when_chat_id_zero(self):
        """config_telegram_logging does nothing when management.logging.chat_id is 0."""
        tg = TelegramSettings(bot_token="tok")
        root_logger = logging.getLogger()
        before = list(root_logger.handlers)
        config_telegram_logging(tg)
        after = list(root_logger.handlers)
        assert before == after

    def test_handler_gets_logging_thread_id(self):
        """config_telegram_logging passes management.logging.message_thread_id through."""
        tg = TelegramSettings(
            bot_token="tok",
            management=ManagementChats(logging=ChatConfig(chat_id=-100111, message_thread_id=5)),
        )
        root_logger = logging.getLogger()
        before = list(root_logger.handlers)
        try:
            config_telegram_logging(tg)
            handler = next(
                h
                for h in root_logger.handlers
                if isinstance(h, TelegramLogHandler) and h not in before
            )
            # pylint: disable=protected-access
            assert handler._message_thread_id == 5
        finally:
            for h in root_logger.handlers[:]:
                if h not in before:
                    root_logger.removeHandler(h)
