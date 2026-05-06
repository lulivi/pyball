"""Tests for TelegramLogHandler, _ManagementFilter, and add_telegram_log_handler."""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

from pyball.logger import TelegramLogHandler, _ManagementFilter, telegram_log_handler
from pyball.settings import ManagementChatSettings, Settings, TelegramSettings


class TestManagementFilter:
    """Tests for the composite logging filter."""

    def setup_method(self):
        """Create a fresh filter instance for each test."""
        self.f = _ManagementFilter()  # pylint: disable=attribute-defined-outside-init

    def _record(self, name: str, level: int) -> logging.LogRecord:
        return logging.LogRecord(
            name=name, level=level, pathname="", lineno=1, msg="msg", args=(), exc_info=None
        )

    def test_pyball_info_passes(self):
        """pyball.* at INFO is forwarded."""
        assert self.f.filter(self._record("pyball.bot", logging.INFO))

    def test_pyball_warning_passes(self):
        """pyball.* at WARNING is forwarded."""
        assert self.f.filter(self._record("pyball.bot.handlers", logging.WARNING))

    def test_pyball_error_passes(self):
        """pyball.* at ERROR is forwarded."""
        assert self.f.filter(self._record("pyball.application", logging.ERROR))

    def test_pyball_debug_blocked(self):
        """pyball.* at DEBUG is NOT forwarded."""
        assert not self.f.filter(self._record("pyball.domain", logging.DEBUG))

    def test_telegram_error_passes(self):
        """telegram at ERROR is forwarded."""
        assert self.f.filter(self._record("telegram", logging.ERROR))

    def test_telegram_ext_error_passes(self):
        """telegram.ext at ERROR is forwarded."""
        assert self.f.filter(self._record("telegram.ext", logging.ERROR))

    def test_telegram_critical_passes(self):
        """telegram at CRITICAL is forwarded."""
        assert self.f.filter(self._record("telegram", logging.CRITICAL))

    def test_telegram_warning_blocked(self):
        """telegram at WARNING is NOT forwarded."""
        assert not self.f.filter(self._record("telegram", logging.WARNING))

    def test_telegram_info_blocked(self):
        """telegram at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("telegram", logging.INFO))

    def test_httpx_info_blocked(self):
        """httpx at INFO is NOT forwarded (not in allowlist)."""
        assert not self.f.filter(self._record("httpx", logging.INFO))

    def test_uvicorn_error_blocked(self):
        """uvicorn at ERROR is NOT forwarded (not in allowlist)."""
        assert not self.f.filter(self._record("uvicorn", logging.ERROR))

    def test_root_logger_info_blocked(self):
        """Root logger ('') at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("", logging.INFO))

    def test_pyball_root_blocked(self):
        """'pyball' (without dot suffix) at INFO is NOT forwarded."""
        assert not self.f.filter(self._record("pyball", logging.INFO))

    def test_telegramfoo_blocked(self):
        """'telegramfoo' (no dot separator) at ERROR is NOT forwarded."""
        assert not self.f.filter(self._record("telegramfoo", logging.ERROR))


class TestTelegramLogHandler:
    """Tests for TelegramLogHandler.emit()."""

    _PATCH = "pyball.logger.urllib.request.urlopen"

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

    def _captured_payload(self, mock_urlopen) -> dict:
        req = mock_urlopen.call_args.args[0]
        return json.loads(req.data)

    def test_emit_posts_to_correct_url(self):
        """emit() calls the Telegram sendMessage endpoint for the configured token."""
        handler = TelegramLogHandler("mytoken", -100111)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record())
        req = mock_urlopen.call_args.args[0]
        assert req.full_url == "https://api.telegram.org/botmytoken/sendMessage"

    def test_emit_sends_chat_id(self):
        """emit() includes the configured chat_id in the payload."""
        handler = TelegramLogHandler("tok", -100999)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record())
        assert self._captured_payload(mock_urlopen)["chat_id"] == -100999

    def test_emit_uses_markdownv2(self):
        """emit() sets parse_mode to MarkdownV2."""
        handler = TelegramLogHandler("tok", -100111)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record())
        assert self._captured_payload(mock_urlopen)["parse_mode"] == "MarkdownV2"

    def test_emit_info_emoji(self):
        """INFO records use the ℹ️ emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(level=logging.INFO))
        assert "ℹ️" in self._captured_payload(mock_urlopen)["text"]

    def test_emit_warning_emoji(self):
        """WARNING records use the ⚠️ emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(level=logging.WARNING))
        assert "⚠️" in self._captured_payload(mock_urlopen)["text"]

    def test_emit_error_emoji(self):
        """ERROR records use the 🔴 emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(level=logging.ERROR))
        assert "🔴" in self._captured_payload(mock_urlopen)["text"]

    def test_emit_critical_emoji(self):
        """CRITICAL records use the 💀 emoji."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(level=logging.CRITICAL))
        assert "💀" in self._captured_payload(mock_urlopen)["text"]

    def test_emit_includes_levelname_and_logger_name_and_lineno(self):
        """Text contains levelname, logger name, and line number."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(name="pyball.bot", level=logging.ERROR, lineno=99))
        text = self._captured_payload(mock_urlopen)["text"]
        assert "ERROR" in text
        assert "pyball.bot" in text
        assert "99" in text

    def test_emit_includes_message(self):
        """Text contains the log message."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record(msg="something broke"))
        assert "something broke" in self._captured_payload(mock_urlopen)["text"]

    def test_emit_includes_traceback_when_exc_info_present(self):
        """Text includes the traceback when the record has exc_info."""
        handler = TelegramLogHandler("tok", -1)
        exc_info = None
        try:
            raise ValueError("kaboom")
        except ValueError:
            exc_info = sys.exc_info()
        record = self._make_record(level=logging.ERROR, exc_info=exc_info)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(record)
        text = self._captured_payload(mock_urlopen)["text"]
        assert "ValueError" in text
        assert "kaboom" in text

    def test_emit_wraps_content_in_code_block(self):
        """Text is wrapped in a MarkdownV2 code block (triple backticks)."""
        handler = TelegramLogHandler("tok", -1)
        with patch(self._PATCH) as mock_urlopen:
            handler.emit(self._make_record())
        text = self._captured_payload(mock_urlopen)["text"]
        assert "```" in text
        assert text.endswith("\n```")

    def test_emit_silences_network_exception(self):
        """Network errors in emit() do not propagate; handleError is called instead."""
        handler = TelegramLogHandler("tok", -1)
        mock_handle_error = MagicMock()
        setattr(handler, "handleError", mock_handle_error)
        record = self._make_record()
        with patch(self._PATCH) as mock_urlopen:
            mock_urlopen.side_effect = OSError("network down")
            handler.emit(record)
        mock_handle_error.assert_called_once_with(record)


class TestTelegramLogHandlerFactory:
    """Tests for telegram_log_handler factory function."""

    def _settings(self, chat_id: int) -> Settings:
        return Settings(
            telegram=TelegramSettings(
                bot_token="tok",
                management=ManagementChatSettings(chat_id=chat_id),
            )
        )

    def test_returns_telegram_handler_when_chat_id_is_set(self):
        """telegram_log_handler returns a TelegramLogHandler when chat_id is configured."""
        handler = telegram_log_handler(self._settings(chat_id=-100111))
        assert isinstance(handler, TelegramLogHandler)

    def test_returned_handler_has_management_filter(self):
        """The returned handler has a _ManagementFilter attached."""
        handler = telegram_log_handler(self._settings(chat_id=-100111))
        assert any(isinstance(f, _ManagementFilter) for f in handler.filters)
